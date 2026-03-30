"""Proxy resolution with Resin-first routing and local fallback."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import threading
import time
from typing import Any, Optional
from urllib.parse import quote, unquote, urlparse, urlunparse

from .config_store import config_store


_PURPOSE_REGISTER = "register"
_PURPOSE_RUNTIME = "runtime"
_DEFAULT_REGISTER_SLOTS_PER_IP = 5
_DEFAULT_REGISTER_WHITELIST_SLOTS_PER_IP = 10
_REGISTER_SLOT_POOL_REFRESH_SECONDS = 60
_RESIN_PLATFORM_KEY_MAP = {
    ("chatgpt", _PURPOSE_REGISTER): "resin_platform_chatgpt_register",
    ("chatgpt", _PURPOSE_RUNTIME): "resin_platform_chatgpt_runtime",
    ("gemini", _PURPOSE_REGISTER): "resin_platform_gemini_register",
    ("gemini", _PURPOSE_RUNTIME): "resin_platform_gemini_runtime",
}


def _get_config_value(key: str, default: str = "") -> str:
    return str(config_store.get(key, default) or default).strip()


def _get_int_config(key: str, default: int) -> int:
    raw = _get_config_value(key, "")
    try:
        return int(raw)
    except Exception:
        return default


def _normalize_gateway_url(raw_url: str) -> str:
    value = str(raw_url or "").strip()
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"http://{value}")
    if not parsed.scheme:
        parsed = urlparse(f"http://{value}")
    netloc = parsed.netloc or parsed.path
    if not netloc:
        return ""
    return urlunparse((parsed.scheme or "http", netloc, "", "", "", "")).rstrip("/")


def _resolve_resin_platform(platform: str, purpose: str) -> str:
    normalized_platform = str(platform or "").strip().lower()
    normalized_purpose = _PURPOSE_RUNTIME if purpose == _PURPOSE_RUNTIME else _PURPOSE_REGISTER
    config_key = _RESIN_PLATFORM_KEY_MAP.get((normalized_platform, normalized_purpose))
    if config_key:
        configured = _get_config_value(config_key, "")
        if configured:
            return configured
    if normalized_platform:
        return f"{normalized_platform}-{normalized_purpose}"
    return "Default"


def _resin_api_base_url() -> str:
    gateway = get_resin_gateway_url()
    return f"{gateway}/api/v1" if gateway else ""


def _resin_admin_headers() -> dict[str, str]:
    token = _get_config_value("resin_admin_token", "")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _sanitize_slot_value(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "-" for ch in str(value or "").strip().lower())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "slot"


def _normalize_slot_whitelist_entries(raw: str) -> set[str]:
    items: set[str] = set()
    for part in str(raw or "").replace(",", "\n").splitlines():
        value = part.strip().lower()
        if value:
            items.add(value)
    return items


def _lease_matches_slot_whitelist(lease: dict[str, Any], whitelist_entries: set[str]) -> bool:
    if not whitelist_entries:
        return False

    egress_ip = str(lease.get("egress_ip") or "").strip().lower()
    node_hash = str(lease.get("node_hash") or "").strip().lower()
    node_tag = str(lease.get("node_tag") or lease.get("display_tag") or "").strip().lower()

    if egress_ip and egress_ip in whitelist_entries:
        return True
    if node_hash and node_hash in whitelist_entries:
        return True
    return bool(node_tag and any(entry in node_tag for entry in whitelist_entries))


def _build_register_slot_account_name(platform_name: str, egress_ip: str, slot_index: int) -> str:
    return (
        f"slot-pool.{_sanitize_slot_value(platform_name)}."
        f"{_sanitize_slot_value(egress_ip)}.slot-{int(slot_index):02d}"
    )


def _build_register_slot_accounts(
    *,
    leases: list[dict[str, Any]],
    platform_name: str,
    default_slots_per_ip: int,
    whitelist_slots_per_ip: int,
    whitelist_entries: set[str],
) -> tuple[list[str], list[dict[str, str]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for lease in leases or []:
        account = str(lease.get("account") or "").strip()
        egress_ip = str(lease.get("egress_ip") or "").strip()
        if not account or not egress_ip:
            continue
        groups.setdefault(egress_ip, []).append(dict(lease))

    accounts: list[str] = []
    inherit_requests: list[dict[str, str]] = []

    for egress_ip in sorted(groups):
        items = groups[egress_ip]
        items.sort(key=lambda item: str(item.get("account") or ""))
        slot_limit = whitelist_slots_per_ip if any(
            _lease_matches_slot_whitelist(item, whitelist_entries) for item in items
        ) else default_slots_per_ip
        slot_limit = max(1, int(slot_limit))

        selected_accounts: list[str] = []
        for item in items:
            account = str(item.get("account") or "").strip()
            if account and account not in selected_accounts:
                selected_accounts.append(account)
            if len(selected_accounts) >= slot_limit:
                break

        accounts.extend(selected_accounts)

        if not selected_accounts:
            continue

        parent_account = selected_accounts[0]
        for slot_index in range(len(selected_accounts) + 1, slot_limit + 1):
            new_account = _build_register_slot_account_name(platform_name, egress_ip, slot_index)
            accounts.append(new_account)
            inherit_requests.append(
                {
                    "parent_account": parent_account,
                    "new_account": new_account,
                }
            )

    return accounts, inherit_requests


def _parse_resin_proxy_identity(url: str) -> tuple[str, str]:
    parsed = urlparse(str(url or ""))
    username = unquote(parsed.username or "").strip()
    if not username:
        return "", ""
    if "." not in username:
        return username, ""
    platform_name, account = username.split(".", 1)
    return platform_name.strip(), account.strip()


def get_resin_gateway_url() -> str:
    return _normalize_gateway_url(_get_config_value("resin_url", ""))


def build_resin_proxy_url(platform: str, purpose: str = _PURPOSE_REGISTER, account: str = "") -> str:
    gateway_url = get_resin_gateway_url()
    if not gateway_url:
        return ""

    token = _get_config_value("resin_proxy_token", "")
    resin_platform = _resolve_resin_platform(platform, purpose)
    account = str(account or "").strip()
    username = resin_platform if not account else f"{resin_platform}.{account}"

    parsed = urlparse(gateway_url)
    encoded_user = quote(username, safe=".-_")
    encoded_token = quote(token, safe="") if token else ""
    if encoded_token:
        auth_netloc = f"{encoded_user}:{encoded_token}@{parsed.netloc}"
    else:
        auth_netloc = f"{encoded_user}@{parsed.netloc}"
    return urlunparse((parsed.scheme, auth_netloc, "", "", "", ""))


def is_resin_proxy_url(url: str | None) -> bool:
    gateway = get_resin_gateway_url()
    if not gateway or not url:
        return False
    target = urlparse(str(url))
    resin = urlparse(gateway)
    return bool(target.hostname and target.hostname == resin.hostname and target.port == resin.port)


class ProxyPool:
    def __init__(self):
        self._index = 0
        self._lock = threading.Lock()
        self._register_slot_lock = threading.Lock()
        self._register_slot_active: dict[str, set[str]] = {}
        self._register_slot_cursor: dict[str, int] = {}
        self._register_slot_cache: dict[str, tuple[float, list[str]]] = {}
        self._resin_platform_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def _get_next_local_proxy(self, region: str = "") -> Optional[str]:
        from sqlmodel import Session, select

        from .db import ProxyModel, engine

        with Session(engine) as s:
            q = select(ProxyModel).where(ProxyModel.is_active == True)
            if region:
                q = q.where(ProxyModel.region == region)
            proxies = s.exec(q).all()
            if not proxies:
                return None
            proxies.sort(
                key=lambda p: p.success_count / max(p.success_count + p.fail_count, 1),
                reverse=True,
            )
            with self._lock:
                idx = self._index % len(proxies)
                self._index += 1
            return proxies[idx].url

    def _fetch_resin_platform_info(self, platform_name: str) -> dict[str, Any] | None:
        import requests

        now = time.time()
        cached = self._resin_platform_cache.get(platform_name)
        if cached and now - cached[0] < _REGISTER_SLOT_POOL_REFRESH_SECONDS:
            return dict(cached[1])

        response = requests.get(
            f"{_resin_api_base_url()}/platforms",
            headers=_resin_admin_headers(),
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json() or {}
        items = list(payload.get("items") or [])
        for item in items:
            if str(item.get("name") or "").strip() == platform_name:
                self._resin_platform_cache[platform_name] = (now, dict(item))
                return dict(item)
        return None

    def _fetch_resin_platform_leases(self, platform_id: str) -> list[dict[str, Any]]:
        import requests

        offset = 0
        limit = 1000
        items: list[dict[str, Any]] = []
        while True:
            response = requests.get(
                (
                    f"{_resin_api_base_url()}/platforms/{platform_id}/leases"
                    f"?limit={limit}&offset={offset}&sort_by=account&sort_order=asc"
                ),
                headers=_resin_admin_headers(),
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json() or {}
            chunk = list(payload.get("items") or [])
            items.extend(chunk)
            total = int(payload.get("total") or len(items))
            offset += len(chunk)
            if not chunk or offset >= total:
                break
        return items

    def _inherit_resin_lease(self, platform_name: str, parent_account: str, new_account: str) -> None:
        import requests

        token = _get_config_value("resin_proxy_token", "")
        gateway = get_resin_gateway_url()
        if not gateway or not token:
            return
        response = requests.post(
            f"{gateway}/{token}/api/v1/{platform_name}/actions/inherit-lease",
            headers={"Content-Type": "application/json"},
            json={
                "parent_account": parent_account,
                "new_account": new_account,
            },
            timeout=20,
        )
        response.raise_for_status()

    def _get_resin_register_slot_accounts(self, platform_name: str) -> list[str]:
        now = time.time()
        cached = self._register_slot_cache.get(platform_name)
        if cached and now - cached[0] < _REGISTER_SLOT_POOL_REFRESH_SECONDS:
            return list(cached[1])

        platform_info = self._fetch_resin_platform_info(platform_name)
        if not platform_info:
            self._register_slot_cache[platform_name] = (now, [])
            return []

        platform_id = str(platform_info.get("id") or "").strip()
        if not platform_id:
            self._register_slot_cache[platform_name] = (now, [])
            return []

        leases = self._fetch_resin_platform_leases(platform_id)
        slot_accounts, inherit_requests = _build_register_slot_accounts(
            leases=leases,
            platform_name=platform_name,
            default_slots_per_ip=max(
                1,
                _get_int_config(
                    "register_resin_slots_per_ip_default",
                    _DEFAULT_REGISTER_SLOTS_PER_IP,
                ),
            ),
            whitelist_slots_per_ip=max(
                1,
                _get_int_config(
                    "register_resin_slots_per_ip_whitelist",
                    _DEFAULT_REGISTER_WHITELIST_SLOTS_PER_IP,
                ),
            ),
            whitelist_entries=_normalize_slot_whitelist_entries(
                _get_config_value("register_resin_slot_whitelist", "")
            ),
        )

        failed_accounts: set[str] = set()
        for request in inherit_requests:
            try:
                self._inherit_resin_lease(
                    platform_name=platform_name,
                    parent_account=request["parent_account"],
                    new_account=request["new_account"],
                )
            except Exception:
                failed_accounts.add(request["new_account"])

        final_accounts = [account for account in slot_accounts if account not in failed_accounts]
        self._register_slot_cache[platform_name] = (now, final_accounts)
        return list(final_accounts)

    def _acquire_resin_register_account(self, platform_name: str, requested_account: str) -> str:
        slot_accounts = self._get_resin_register_slot_accounts(platform_name)
        if not slot_accounts:
            return requested_account

        with self._register_slot_lock:
            active_accounts = self._register_slot_active.setdefault(platform_name, set())
            cursor = self._register_slot_cursor.get(platform_name, 0)
            for offset in range(len(slot_accounts)):
                index = (cursor + offset) % len(slot_accounts)
                account = slot_accounts[index]
                if account in active_accounts:
                    continue
                active_accounts.add(account)
                self._register_slot_cursor[platform_name] = (index + 1) % len(slot_accounts)
                return account

        return requested_account

    def release_register_proxy(self, url: str | None) -> None:
        if not is_resin_proxy_url(url):
            return

        platform_name, account = _parse_resin_proxy_identity(str(url or ""))
        if not platform_name or not account:
            return

        with self._register_slot_lock:
            active_accounts = self._register_slot_active.get(platform_name)
            if not active_accounts or account not in active_accounts:
                return
            active_accounts.discard(account)
            if not active_accounts:
                self._register_slot_active.pop(platform_name, None)

    def get_next(
        self,
        region: str = "",
        *,
        platform: str = "",
        purpose: str = _PURPOSE_REGISTER,
        account: str = "",
    ) -> Optional[str]:
        resin_account = account
        if purpose == _PURPOSE_REGISTER:
            resin_platform = _resolve_resin_platform(platform, purpose)
            resin_account = self._acquire_resin_register_account(resin_platform, account)
        resin_proxy = build_resin_proxy_url(platform=platform, purpose=purpose, account=resin_account)
        if resin_proxy:
            return resin_proxy
        return self._get_next_local_proxy(region)

    def report_success(self, url: str) -> None:
        if is_resin_proxy_url(url):
            return
        from sqlmodel import Session, select

        from .db import ProxyModel, engine

        with Session(engine) as s:
            p = s.exec(select(ProxyModel).where(ProxyModel.url == url)).first()
            if p:
                p.success_count += 1
                p.last_checked = datetime.now(timezone.utc)
                s.add(p)
                s.commit()

    def report_fail(self, url: str) -> None:
        if is_resin_proxy_url(url):
            return
        from sqlmodel import Session, select

        from .db import ProxyModel, engine

        with Session(engine) as s:
            p = s.exec(select(ProxyModel).where(ProxyModel.url == url)).first()
            if p:
                p.fail_count += 1
                p.last_checked = datetime.now(timezone.utc)
                if p.fail_count > 0 and p.success_count == 0 and p.fail_count >= 5:
                    p.is_active = False
                s.add(p)
                s.commit()

    def check_all(self) -> dict:
        """Check local fallback proxies only."""
        import requests
        from sqlmodel import Session, select

        from .db import ProxyModel, engine

        with Session(engine) as s:
            proxies = s.exec(select(ProxyModel)).all()
        results = {"ok": 0, "fail": 0}
        for p in proxies:
            try:
                r = requests.get(
                    "https://httpbin.org/ip",
                    proxies={"http": p.url, "https": p.url},
                    timeout=8,
                )
                if r.status_code == 200:
                    self.report_success(p.url)
                    results["ok"] += 1
                    continue
            except Exception:
                pass
            self.report_fail(p.url)
            results["fail"] += 1
        return results


proxy_pool = ProxyPool()
