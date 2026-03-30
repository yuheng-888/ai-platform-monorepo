"""GoProxy -> Resin subscription synchronization."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any, Iterable
from urllib.parse import urlencode, urlparse, urlunparse

import requests

from core.config_store import config_store


_QUALITY_ORDER = {"C": 0, "B": 1, "A": 2, "S": 3}
_DEFAULT_GOPROXY_URL = "http://127.0.0.1:7778"
_DEFAULT_SUBSCRIPTION_NAME = "goproxy-pool"
_DEFAULT_INTERVAL_SECONDS = 600
_BLOCKED_EXIT_LOCATION_PHRASES = {
    "INDIANA",
    "INDIANAPOLIS",
    "RUSSIA",
    "RUSSIAN",
    "MOSCOW",
    "ST PETERSBURG",
    "SAINT PETERSBURG",
}

_LAST_SYNC_STATE: dict[str, Any] = {
    "ok": False,
    "action": "",
    "message": "never_run",
    "fetched": 0,
    "accepted": 0,
    "subscription_id": "",
    "subscription_name": "",
    "last_started_at": 0,
    "last_finished_at": 0,
    "triggered": False,
}


def _get_config_value(key: str, default: str = "") -> str:
    return str(config_store.get(key, default) or default).strip()


def _normalize_base_url(raw_url: str, default: str = "") -> str:
    value = str(raw_url or "").strip() or str(default or "").strip()
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"http://{value}")
    netloc = parsed.netloc or parsed.path
    if not netloc:
        return ""
    return urlunparse((parsed.scheme or "http", netloc, "", "", "", "")).rstrip("/")


def _get_bool(key: str, default: bool = False) -> bool:
    raw = _get_config_value(key, "")
    if raw.lower() in {"1", "true", "yes", "on"}:
        return True
    if raw.lower() in {"0", "false", "no", "off"}:
        return False
    return default


def _get_int(key: str, default: int) -> int:
    raw = _get_config_value(key, "")
    try:
        return int(raw)
    except Exception:
        return default


def _goproxy_base_url() -> str:
    return _normalize_base_url(_get_config_value("goproxy_upstream_url", ""), _DEFAULT_GOPROXY_URL)


def _resin_base_url() -> str:
    return _normalize_base_url(_get_config_value("resin_url", ""))


def _resin_api_base_url() -> str:
    base = _resin_base_url()
    if not base:
        return ""
    return f"{base}/api/v1"


def _resin_admin_headers() -> dict[str, str]:
    token = _get_config_value("resin_admin_token", "")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _subscription_name() -> str:
    return _get_config_value("goproxy_resin_subscription_name", _DEFAULT_SUBSCRIPTION_NAME) or _DEFAULT_SUBSCRIPTION_NAME


def _min_quality() -> str:
    value = _get_config_value("goproxy_resin_min_quality", "B").upper()
    return value if value in _QUALITY_ORDER else "B"


def _max_latency_ms() -> int:
    return max(0, _get_int("goproxy_resin_max_latency_ms", 2000))


def _sync_interval_seconds() -> int:
    return max(60, _get_int("goproxy_resin_sync_interval_seconds", _DEFAULT_INTERVAL_SECONDS))


def _sync_enabled() -> bool:
    return _get_bool("goproxy_resin_sync_enabled", False)


def _quality_score(value: str) -> int:
    return _QUALITY_ORDER.get(str(value or "").upper(), -1)


def _normalize_exit_location(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[-_/,\t]+", " ", raw)).strip()


def _is_blocked_exit_location(value: Any) -> bool:
    normalized = _normalize_exit_location(value)
    if not normalized:
        return False

    parts = normalized.split(" ")
    if parts and parts[0] == "RU":
        return True

    return any(phrase in normalized for phrase in _BLOCKED_EXIT_LOCATION_PHRASES)


def filter_goproxy_proxies(rows: Iterable[dict[str, Any]], *, min_quality: str, max_latency_ms: int) -> list[dict[str, Any]]:
    threshold = _quality_score(min_quality)
    chosen: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in rows or []:
        protocol = str(raw.get("protocol") or "").strip().lower()
        address = str(raw.get("address") or "").strip()
        status = str(raw.get("status") or "").strip().lower()
        quality = str(raw.get("quality_grade") or "").strip().upper()
        exit_location = raw.get("exit_location")
        latency = raw.get("latency")
        try:
            latency_value = int(latency or 0)
        except Exception:
            latency_value = 0

        if protocol not in {"http", "socks5"} or not address:
            continue
        if status != "active":
            continue
        if _quality_score(quality) < threshold:
            continue
        if max_latency_ms > 0 and latency_value > max_latency_ms:
            continue
        if _is_blocked_exit_location(exit_location):
            continue

        normalized = dict(raw)
        normalized["protocol"] = protocol
        normalized["address"] = address
        normalized["status"] = "active"
        normalized["quality_grade"] = quality
        normalized["latency"] = latency_value

        key = (protocol, address)
        previous = chosen.get(key)
        if not previous or latency_value < int(previous.get("latency") or 0):
            chosen[key] = normalized

    return list(chosen.values())


def build_resin_subscription_content(rows: Iterable[dict[str, Any]]) -> str:
    lines: list[str] = []
    for row in rows or []:
        protocol = str(row.get("protocol") or "").strip().lower()
        address = str(row.get("address") or "").strip()
        if protocol in {"http", "socks5"} and address:
            lines.append(f"{protocol}://{address}")
    return "\n".join(lines)


def _fetch_goproxy_proxies() -> list[dict[str, Any]]:
    url = f"{_goproxy_base_url()}/api/proxies"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []


def _list_resin_subscriptions(name: str) -> list[dict[str, Any]]:
    query = urlencode(
        {
            "keyword": name,
            "limit": 100,
            "offset": 0,
            "sort_by": "created_at",
            "sort_order": "desc",
        }
    )
    response = requests.get(
        f"{_resin_api_base_url()}/subscriptions?{query}",
        headers=_resin_admin_headers(),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json() or {}
    return list(payload.get("items") or [])


def _create_resin_subscription(name: str, content: str) -> dict[str, Any]:
    response = requests.post(
        f"{_resin_api_base_url()}/subscriptions",
        headers=_resin_admin_headers(),
        json={
            "name": name,
            "source_type": "local",
            "content": content,
            "enabled": True,
            "ephemeral": True,
            "ephemeral_node_evict_delay": "72h",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json() or {}


def _update_resin_subscription(subscription_id: str, content: str) -> dict[str, Any]:
    response = requests.patch(
        f"{_resin_api_base_url()}/subscriptions/{subscription_id}",
        headers=_resin_admin_headers(),
        json={"content": content, "enabled": True, "ephemeral": True, "ephemeral_node_evict_delay": "72h"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json() or {}


def _refresh_resin_subscription(subscription_id: str) -> None:
    response = requests.post(
        f"{_resin_api_base_url()}/subscriptions/{subscription_id}/actions/refresh",
        headers=_resin_admin_headers(),
        timeout=20,
    )
    response.raise_for_status()


def _set_last_sync_state(**updates: Any) -> dict[str, Any]:
    _LAST_SYNC_STATE.update(updates)
    return deepcopy(_LAST_SYNC_STATE)


def get_goproxy_resin_sync_status() -> dict[str, Any]:
    return deepcopy(_LAST_SYNC_STATE)


def sync_goproxy_into_resin(*, force: bool = False) -> dict[str, Any]:
    started_at = int(datetime.now(timezone.utc).timestamp())
    _set_last_sync_state(triggered=force, last_started_at=started_at)

    goproxy_url = _goproxy_base_url()
    resin_api = _resin_api_base_url()
    subscription_name = _subscription_name()
    if not goproxy_url:
        return _set_last_sync_state(ok=False, action="", message="goproxy_not_configured", last_finished_at=started_at)
    if not resin_api:
        return _set_last_sync_state(ok=False, action="", message="resin_not_configured", last_finished_at=started_at)

    try:
        fetched_rows = _fetch_goproxy_proxies()
        filtered = filter_goproxy_proxies(
            fetched_rows,
            min_quality=_min_quality(),
            max_latency_ms=_max_latency_ms(),
        )
        content = build_resin_subscription_content(filtered)
        subscriptions = _list_resin_subscriptions(subscription_name)
        current = next((item for item in subscriptions if str(item.get("name") or "").strip() == subscription_name), None)

        if current:
            subscription_id = str(current.get("id") or "")
            updated = _update_resin_subscription(subscription_id, content)
            action = "updated"
            subscription_id = str(updated.get("id") or subscription_id)
        else:
            created = _create_resin_subscription(subscription_name, content)
            action = "created"
            subscription_id = str(created.get("id") or "")

        if subscription_id:
            _refresh_resin_subscription(subscription_id)

        finished_at = int(datetime.now(timezone.utc).timestamp())
        return _set_last_sync_state(
            ok=True,
            action=action,
            message="ok",
            fetched=len(fetched_rows),
            accepted=len(filtered),
            subscription_id=subscription_id,
            subscription_name=subscription_name,
            last_finished_at=finished_at,
        )
    except Exception as exc:
        finished_at = int(datetime.now(timezone.utc).timestamp())
        return _set_last_sync_state(
            ok=False,
            action="",
            message=str(exc),
            subscription_name=subscription_name,
            last_finished_at=finished_at,
        )


def sync_goproxy_into_resin_if_due(*, now: int | None = None) -> dict[str, Any]:
    current = int(now if now is not None else datetime.now(timezone.utc).timestamp())
    if not _sync_enabled():
        return {**get_goproxy_resin_sync_status(), "triggered": False, "reason": "disabled"}

    last_started_at = int(_LAST_SYNC_STATE.get("last_started_at") or 0)
    if last_started_at and current - last_started_at < _sync_interval_seconds():
        return {**get_goproxy_resin_sync_status(), "triggered": False, "reason": "interval_not_elapsed"}

    result = sync_goproxy_into_resin(force=False)
    return {**result, "triggered": True, "reason": "due"}
