"""Gemini Business 请求绑定辅助。"""

from __future__ import annotations


def normalize_forced_account_id(raw_value: str | None) -> str | None:
    normalized = str(raw_value or "").strip()
    return normalized or None


def scope_conversation_key(base_key: str, forced_account_id: str | None) -> str:
    normalized = normalize_forced_account_id(forced_account_id)
    if not normalized:
        return base_key
    return f"{base_key}::account:{normalized}"
