"""Gemini Business -> CLIProxyAPI 同步适配器。"""

from __future__ import annotations

import time
from typing import Any

import requests

from services.cliproxyapi_sync import (
    DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY,
    _build_upload_url,
    _extract_error_message,
    resolve_cliproxyapi_url,
)
from services.external_apps import _main_site_public_url


def _get_config_value(key: str, default: str = "") -> str:
    try:
        from core.config_store import config_store

        return str(config_store.get(key, default) or "").strip()
    except Exception:
        return default


def is_cliproxyapi_enabled(api_url: str | None = None) -> bool:
    return bool(resolve_cliproxyapi_url(api_url))


def _resolve_runtime_url(runtime_url: str | None = None) -> str:
    resolved = str(runtime_url or "").strip().rstrip("/")
    if resolved:
        return resolved
    return f"{_main_site_public_url().rstrip('/')}/gemini/v1"


def _resolve_gemini_admin_key(admin_key: str | None = None) -> str:
    resolved = str(admin_key or "").strip()
    if resolved:
        return resolved
    return _get_config_value("gemini_admin_key", "")


def _resolve_account_id(account: Any) -> str:
    extra = dict(getattr(account, "extra", None) or {})
    return str(
        extra.get("gemini_account_id")
        or getattr(account, "user_id", "")
        or getattr(account, "email", "")
        or ""
    ).strip()


def build_gemini_business_auth_payload(
    account: Any,
    *,
    runtime_url: str | None = None,
    admin_key: str | None = None,
) -> dict[str, Any]:
    extra = dict(getattr(account, "extra", None) or {})
    email = str(getattr(account, "email", "") or extra.get("mail_address") or "").strip()
    account_id = _resolve_account_id(account)
    resolved_runtime_url = _resolve_runtime_url(runtime_url)
    resolved_admin_key = _resolve_gemini_admin_key(admin_key)

    payload: dict[str, Any] = {
        "type": "gemini-business",
        "email": email,
        "gemini_account_id": account_id,
        "base_url": resolved_runtime_url,
        "api_key": resolved_admin_key,
        "header:X-Gemini-Account-ID": account_id,
        "mail_address": str(extra.get("mail_address") or email).strip(),
        "secure_c_ses": extra.get("secure_c_ses"),
        "host_c_oses": extra.get("host_c_oses"),
        "csesidx": extra.get("csesidx"),
        "config_id": extra.get("config_id"),
        "expires_at": extra.get("expires_at"),
    }
    return payload


def _auth_models_ready(
    *,
    api_url: str,
    management_key: str,
    filename: str,
    timeout: int = 30,
) -> bool:
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/v0/management/auth-files/models",
            params={"name": filename},
            headers={"Authorization": f"Bearer {management_key}"},
            timeout=timeout,
        )
    except Exception:
        return False

    if response.status_code != 200:
        return False

    try:
        data = response.json()
    except Exception:
        return False
    return bool((data.get("models") or []))


def sync_gemini_account_to_cliproxyapi(
    account: Any,
    *,
    api_url: str | None = None,
    management_key: str | None = None,
    runtime_url: str | None = None,
    admin_key: str | None = None,
    timeout: int = 30,
) -> tuple[bool, str]:
    resolved_url = resolve_cliproxyapi_url(api_url)
    if not resolved_url:
        return False, "CLIProxyAPI URL 未配置"

    resolved_key = str(management_key or _get_config_value("cliproxyapi_management_key", "")).strip()
    if not resolved_key:
        resolved_key = DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY

    payload = build_gemini_business_auth_payload(
        account,
        runtime_url=runtime_url,
        admin_key=admin_key,
    )
    if not payload["email"]:
        return False, "缺少邮箱，无法同步到 CLIProxyAPI"
    if not payload["gemini_account_id"]:
        return False, "缺少 Gemini 账号 ID，无法同步到 CLIProxyAPI"
    if not payload["api_key"]:
        return False, "缺少 Gemini 运行时管理密钥，无法同步到 CLIProxyAPI"

    filename = f"{payload['email']}.json"
    upload_url = _build_upload_url(resolved_url, filename)
    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
    }

    def _post_once() -> requests.Response:
        return requests.post(
            upload_url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )

    try:
        response = _post_once()
    except Exception as exc:
        return False, f"CLIProxyAPI 上传异常: {exc}"

    if response.status_code in (200, 201):
        if _auth_models_ready(api_url=resolved_url, management_key=resolved_key, filename=filename, timeout=timeout):
            return True, "上传成功"
        time.sleep(1)
        if _auth_models_ready(api_url=resolved_url, management_key=resolved_key, filename=filename, timeout=timeout):
            return True, "上传成功"
        try:
            response = _post_once()
        except Exception as exc:
            return False, f"CLIProxyAPI 上传后补写异常: {exc}"
        if response.status_code in (200, 201):
            time.sleep(1)
            if _auth_models_ready(api_url=resolved_url, management_key=resolved_key, filename=filename, timeout=timeout):
                return True, "上传成功"
            return True, "上传成功"

    detail = _extract_error_message(response)
    if detail:
        return False, f"CLIProxyAPI 上传失败: {detail}"
    return False, f"CLIProxyAPI 上传失败: HTTP {response.status_code}"
