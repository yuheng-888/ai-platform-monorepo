from __future__ import annotations

from typing import Any


GEMINI_SHARED_MAIN_SITE_CONFIG_KEYS = {
    "mail_provider",
    "register_max_concurrency",
    "register_domain",
    "duckmail_provider_url",
    "duckmail_bearer",
    "duckmail_verify_ssl",
    "moemail_api_url",
    "moemail_api_key",
    "moemail_domain",
    "freemail_api_url",
    "freemail_admin_token",
    "freemail_domain",
    "freemail_verify_ssl",
    "gptmail_base_url",
    "gptmail_api_key",
    "gptmail_domain",
    "gptmail_verify_ssl",
    "cfmail_base_url",
    "cfmail_api_key",
    "cfmail_domain",
    "cfmail_verify_ssl",
}


def _parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    lowered = str(value).strip().lower()
    if lowered in ("1", "true", "yes", "y", "on"):
        return True
    if lowered in ("0", "false", "no", "n", "off"):
        return False
    return default


def _parse_int(value: Any, default: int) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return default
    return parsed if parsed > 0 else default


def apply_main_site_shared_config(config_data: dict[str, Any], shared_values: dict[str, Any] | None) -> dict[str, Any]:
    shared_values = shared_values or {}
    basic = config_data.setdefault("basic", {})

    string_mappings = {
        "mail_provider": "temp_mail_provider",
        "register_domain": "register_domain",
        "duckmail_provider_url": "duckmail_base_url",
        "duckmail_bearer": "duckmail_api_key",
        "moemail_api_url": "moemail_base_url",
        "moemail_api_key": "moemail_api_key",
        "moemail_domain": "moemail_domain",
        "freemail_api_url": "freemail_base_url",
        "freemail_admin_token": "freemail_jwt_token",
        "freemail_domain": "freemail_domain",
        "gptmail_base_url": "gptmail_base_url",
        "gptmail_api_key": "gptmail_api_key",
        "gptmail_domain": "gptmail_domain",
        "cfmail_base_url": "cfmail_base_url",
        "cfmail_api_key": "cfmail_api_key",
        "cfmail_domain": "cfmail_domain",
    }
    for source_key, target_key in string_mappings.items():
        if source_key not in shared_values:
            continue
        value = shared_values.get(source_key)
        if value in (None, ""):
            continue
        basic[target_key] = str(value).strip()

    bool_mappings = {
        "duckmail_verify_ssl": "duckmail_verify_ssl",
        "freemail_verify_ssl": "freemail_verify_ssl",
        "gptmail_verify_ssl": "gptmail_verify_ssl",
        "cfmail_verify_ssl": "cfmail_verify_ssl",
    }
    for source_key, target_key in bool_mappings.items():
        if source_key not in shared_values:
            continue
        basic[target_key] = _parse_bool(shared_values.get(source_key), True)

    if "register_max_concurrency" in shared_values:
        basic["register_max_concurrency"] = _parse_int(
            shared_values.get("register_max_concurrency"),
            int(basic.get("register_max_concurrency") or 10),
        )

    return config_data
