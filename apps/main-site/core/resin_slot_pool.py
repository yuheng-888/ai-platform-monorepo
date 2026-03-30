from __future__ import annotations

from typing import Any


def sanitize_slot_value(value: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "-" for ch in str(value or "").strip().lower())
    collapsed = "-".join(part for part in normalized.split("-") if part)
    return collapsed or "slot"


def normalize_slot_whitelist_entries(raw: str) -> set[str]:
    items: set[str] = set()
    for part in str(raw or "").replace(",", "\n").splitlines():
        value = part.strip().lower()
        if value:
            items.add(value)
    return items


def lease_matches_slot_whitelist(lease: dict[str, Any], whitelist_entries: set[str]) -> bool:
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


def build_register_slot_account_name(platform_name: str, egress_ip: str, slot_index: int) -> str:
    return (
        f"slot-pool.{sanitize_slot_value(platform_name)}."
        f"{sanitize_slot_value(egress_ip)}.slot-{int(slot_index):02d}"
    )


def build_register_slot_accounts(
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
            lease_matches_slot_whitelist(item, whitelist_entries) for item in items
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
            new_account = build_register_slot_account_name(platform_name, egress_ip, slot_index)
            accounts.append(new_account)
            inherit_requests.append(
                {
                    "parent_account": parent_account,
                    "new_account": new_account,
                }
            )

    return accounts, inherit_requests


def parse_resin_proxy_identity(url: str) -> tuple[str, str]:
    from urllib.parse import unquote, urlparse

    parsed = urlparse(str(url or ""))
    username = unquote(parsed.username or "").strip()
    if not username:
        return "", ""
    if "." not in username:
        return username, ""
    platform_name, account = username.split(".", 1)
    return platform_name.strip(), account.strip()
