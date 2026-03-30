from fastapi import APIRouter
from pydantic import BaseModel
from core.config_store import config_store
from services import external_apps
from embedded.gemini_business2api.shared_config import GEMINI_SHARED_MAIN_SITE_CONFIG_KEYS

router = APIRouter(prefix="/config", tags=["config"])

CONFIG_KEYS = [
    "laoudo_auth", "laoudo_email", "laoudo_account_id",
    "yescaptcha_key", "twocaptcha_key",
    "default_executor", "default_captcha_solver",
    "register_max_concurrency",
    "register_domain",
    "register_resin_slots_per_ip_default",
    "register_resin_slots_per_ip_whitelist",
    "register_resin_slot_whitelist",
    "duckmail_api_url", "duckmail_provider_url", "duckmail_bearer", "duckmail_verify_ssl",
    "freemail_api_url", "freemail_admin_token", "freemail_username", "freemail_password", "freemail_domain", "freemail_verify_ssl",
    "moemail_api_url", "moemail_api_key", "moemail_domain",
    "mail_provider",
    "gptmail_base_url", "gptmail_api_key", "gptmail_domain", "gptmail_verify_ssl",
    "cfmail_base_url", "cfmail_api_key", "cfmail_domain", "cfmail_verify_ssl",
    "cfworker_api_url", "cfworker_admin_token", "cfworker_domain", "cfworker_fingerprint",
    "luckmail_base_url", "luckmail_api_key", "luckmail_email_type", "luckmail_domain",
    "cpa_api_url", "cpa_api_key",
    "team_manager_url", "team_manager_key",
    "cliproxyapi_url", "cliproxyapi_management_key",
    "resin_url", "resin_admin_token", "resin_proxy_token",
    "resin_platform_chatgpt_register", "resin_platform_chatgpt_runtime",
    "resin_platform_gemini_register", "resin_platform_gemini_runtime",
    "goproxy_enabled", "goproxy_upstream_url", "goproxy_webui_password",
    "goproxy_resin_sync_enabled", "goproxy_resin_sync_interval_seconds",
    "goproxy_resin_subscription_name", "goproxy_resin_min_quality", "goproxy_resin_max_latency_ms",
    "chatgpt_auto_restock_enabled",
    "chatgpt_auto_restock_threshold",
    "chatgpt_auto_restock_target",
    "chatgpt_auto_restock_batch_size",
    "chatgpt_auto_restock_concurrency",
    "chatgpt_auto_restock_proxy",
    "chatgpt_auto_restock_executor_type",
    "chatgpt_auto_restock_captcha_solver",
    "grok2api_url", "grok2api_app_key", "grok2api_pool", "grok2api_quota",
    "gemini_admin_key", "gemini_session_secret",
    "kiro_manager_path", "kiro_manager_exe",
]


class ConfigUpdate(BaseModel):
    data: dict


_SERVICE_RESTART_KEYS = {
    "cliproxyapi": {"cliproxyapi_management_key"},
    "cpa-codex-cleanup": {"cliproxyapi_url", "cliproxyapi_management_key"},
    "resin": {"resin_admin_token", "resin_proxy_token"},
    "goproxy": {"goproxy_webui_password"},
}


def _restart_services_for_keys(updated_keys: set[str]) -> tuple[list[str], dict[str, str]]:
    restarted: list[str] = []
    errors: dict[str, str] = {}

    for service_name, trigger_keys in _SERVICE_RESTART_KEYS.items():
        if not (updated_keys & trigger_keys):
            continue
        status = external_apps._status_one(service_name)
        if not status.get("repo_exists") or not status.get("running"):
            continue
        try:
            external_apps.stop(service_name)
            external_apps.start(service_name)
            restarted.append(service_name)
        except Exception as exc:
            errors[service_name] = str(exc)
    return restarted, errors


def _reload_embedded_gemini_for_keys(updated_keys: set[str]) -> list[str]:
    if not (updated_keys & GEMINI_SHARED_MAIN_SITE_CONFIG_KEYS):
        return []
    try:
        from embedded.gemini_business2api.core.config import config_manager

        config_manager.reload()
        return ["embedded-gemini"]
    except Exception:
        return []


@router.get("")
def get_config():
    all_cfg = config_store.get_all()
    # 只返回已知 key，未设置的返回空字符串
    return {k: all_cfg.get(k, "") for k in CONFIG_KEYS}


@router.put("")
def update_config(body: ConfigUpdate):
    # 只允许更新已知 key
    safe = {k: v for k, v in body.data.items() if k in CONFIG_KEYS}
    config_store.set_many(safe)
    restarted, restart_errors = _restart_services_for_keys(set(safe.keys()))
    reloaded = _reload_embedded_gemini_for_keys(set(safe.keys()))
    return {
        "ok": True,
        "updated": list(safe.keys()),
        "restarted": restarted,
        "restart_errors": restart_errors,
        "reloaded": reloaded,
    }
