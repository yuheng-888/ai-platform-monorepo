"""CLIProxyAPI 同步适配器。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from platforms.chatgpt.cpa_upload import generate_token_json


DEFAULT_CLIPROXYAPI_URL = "http://127.0.0.1:8317"
DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY = "cliproxyapi"
_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_CLIPROXYAPI_REPO = _ROOT / "_ext_targets" / "CLIProxyAPI"


def _get_config_value(key: str, default: str = "") -> str:
    try:
        from core.config_store import config_store

        return str(config_store.get(key, default) or "").strip()
    except Exception:
        return default


def resolve_cliproxyapi_url(api_url: str | None = None) -> str:
    """优先使用显式配置；否则在已接管本地实例时回落到默认地址。"""
    resolved = str(api_url or _get_config_value("cliproxyapi_url", "")).strip()
    if resolved:
        return resolved.rstrip("/")
    if _LOCAL_CLIPROXYAPI_REPO.exists():
        return DEFAULT_CLIPROXYAPI_URL
    return ""


def is_cliproxyapi_enabled(api_url: str | None = None) -> bool:
    return bool(resolve_cliproxyapi_url(api_url))


def _exportable_chatgpt_account(account) -> Any:
    class _Account:
        pass

    extra = getattr(account, "extra", {}) or {}
    exported = _Account()
    exported.email = getattr(account, "email", "")
    exported.access_token = extra.get("access_token") or getattr(account, "token", "")
    exported.refresh_token = extra.get("refresh_token", "")
    exported.id_token = extra.get("id_token", "")
    return exported


def _build_upload_url(api_url: str, filename: str) -> str:
    base = api_url.rstrip("/")
    return f"{base}/v0/management/auth-files?name={quote(filename, safe='')}"


def _extract_error_message(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            return str(data.get("error") or data.get("message") or data.get("status") or "").strip()
    except Exception:
        pass
    return response.text[:200].strip()


def sync_chatgpt_account_to_cliproxyapi(
    account,
    *,
    api_url: str | None = None,
    management_key: str | None = None,
    timeout: int = 30,
) -> tuple[bool, str]:
    """将 ChatGPT/Codex 账号写入 CLIProxyAPI 管理接口。"""
    resolved_url = resolve_cliproxyapi_url(api_url)
    if not resolved_url:
        return False, "CLIProxyAPI URL 未配置"

    resolved_key = str(management_key or _get_config_value("cliproxyapi_management_key", "")).strip()
    if not resolved_key:
        resolved_key = DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY

    token_data = generate_token_json(_exportable_chatgpt_account(account))
    email = str(token_data.get("email") or getattr(account, "email", "") or "").strip()
    if not email:
        return False, "缺少邮箱，无法同步到 CLIProxyAPI"

    upload_url = _build_upload_url(resolved_url, f"{email}.json")
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            upload_url,
            headers=headers,
            json=token_data,
            timeout=timeout,
        )
    except Exception as e:
        return False, f"CLIProxyAPI 上传异常: {e}"

    if response.status_code in (200, 201):
        return True, "上传成功"

    detail = _extract_error_message(response)
    if detail:
        return False, f"CLIProxyAPI 上传失败: {detail}"
    return False, f"CLIProxyAPI 上传失败: HTTP {response.status_code}"
