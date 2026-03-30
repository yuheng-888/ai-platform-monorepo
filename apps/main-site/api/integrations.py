from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from core.base_platform import Account, AccountStatus
from core.db import AccountModel, engine
from services.external_apps import install, list_status, start, start_all, stop, stop_all

router = APIRouter(prefix="/integrations", tags=["integrations"])
_GOPROXY_PROXY_PREFIX = "/api/integrations/goproxy"
_GOPROXY_UPSTREAM = "http://127.0.0.1:7778"
_RESPONSE_HEADER_EXCLUDES = {"content-length", "transfer-encoding", "connection", "content-encoding"}


class BackfillRequest(BaseModel):
    platforms: list[str] = Field(default_factory=lambda: ["grok", "kiro"])


def _to_account(model: AccountModel) -> Account:
    return Account(
        platform=model.platform,
        email=model.email,
        password=model.password,
        user_id=model.user_id,
        region=model.region,
        token=model.token,
        status=AccountStatus(model.status),
        extra=model.get_extra(),
    )


def _rewrite_goproxy_text(text: str) -> str:
    replacements = [
        ('"/api/', f'"{_GOPROXY_PROXY_PREFIX}/api/'),
        ("'/api/", f"'{_GOPROXY_PROXY_PREFIX}/api/"),
        ('"/login"', f'"{_GOPROXY_PROXY_PREFIX}/login"'),
        ("'/login'", f"'{_GOPROXY_PROXY_PREFIX}/login'"),
        ('"/logout"', f'"{_GOPROXY_PROXY_PREFIX}/logout"'),
        ("'/logout'", f"'{_GOPROXY_PROXY_PREFIX}/logout'"),
        ('href="/"', f'href="{_GOPROXY_PROXY_PREFIX}/"'),
        ('action="/"', f'action="{_GOPROXY_PROXY_PREFIX}/"'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_goproxy_body(content: bytes, content_type: str) -> bytes:
    normalized = (content_type or "").lower()
    if not content or ("html" not in normalized and "javascript" not in normalized):
        return content
    text = content.decode("utf-8", errors="ignore")
    return _rewrite_goproxy_text(text).encode("utf-8")


def _rewrite_goproxy_location(location: str) -> str:
    if not location:
        return location
    if location.startswith(_GOPROXY_PROXY_PREFIX):
        return location
    if location.startswith("/"):
        return f"{_GOPROXY_PROXY_PREFIX}{location}"
    return location


def _rewrite_goproxy_set_cookie(value: str) -> str:
    if not value:
        return value
    return value.replace("Path=/;", f"Path={_GOPROXY_PROXY_PREFIX};").replace(
        "path=/;", f"path={_GOPROXY_PROXY_PREFIX};"
    )


def _forwardable_request_headers(request: Request) -> dict[str, str]:
    allowed = {"accept", "content-type", "cookie", "origin", "referer", "user-agent", "x-requested-with"}
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() in allowed:
            headers[key] = value
    return headers


def _apply_proxy_response_headers(target: Response, headers: Iterable[tuple[str, str]]) -> None:
    for key, value in headers:
        normalized = key.lower()
        if normalized in _RESPONSE_HEADER_EXCLUDES:
            continue
        if normalized == "location":
            value = _rewrite_goproxy_location(value)
        elif normalized == "set-cookie":
            value = _rewrite_goproxy_set_cookie(value)
        target.headers.append(key, value)


async def _proxy_goproxy(request: Request, proxy_path: str) -> Response:
    upstream_path = proxy_path or ""
    upstream_url = f"{_GOPROXY_UPSTREAM.rstrip('/')}/{upstream_path.lstrip('/')}"
    body = await request.body()

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0), follow_redirects=False) as client:
        upstream = await client.request(
            request.method,
            upstream_url,
            params=list(request.query_params.multi_items()),
            content=body if body else None,
            headers=_forwardable_request_headers(request),
        )

    rewritten_body = _rewrite_goproxy_body(upstream.content, upstream.headers.get("content-type", ""))
    response = Response(content=rewritten_body, status_code=upstream.status_code)
    _apply_proxy_response_headers(response, upstream.headers.multi_items())
    return response


@router.get("/services")
def get_services():
    return {"items": list_status()}


@router.post("/services/start-all")
def start_all_services():
    return {"items": start_all()}


@router.post("/services/stop-all")
def stop_all_services():
    return {"items": stop_all()}


@router.post("/services/{name}/start")
def start_service(name: str):
    return start(name)


@router.post("/services/{name}/install")
def install_service(name: str):
    return install(name)


@router.post("/services/{name}/stop")
def stop_service(name: str):
    return stop(name)


@router.api_route("/goproxy", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_goproxy_root(request: Request):
    return await _proxy_goproxy(request, "")


@router.api_route("/goproxy/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy_goproxy_path(proxy_path: str, request: Request):
    return await _proxy_goproxy(request, proxy_path)


@router.post("/backfill")
def backfill_integrations(body: BackfillRequest):
    summary = {"total": 0, "success": 0, "failed": 0, "items": []}
    targets = set(body.platforms or [])

    if "grok" in targets:
        from services.grok2api_runtime import ensure_grok2api_ready

        ok, msg = ensure_grok2api_ready()
        if not ok:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "items": [{"platform": "grok", "email": "", "results": [{"name": "grok2api", "ok": False, "msg": msg}]}],
            }

    with Session(engine) as s:
        rows = s.exec(
            select(AccountModel).where(AccountModel.platform.in_(targets))
        ).all()

    for row in rows:
        item = {"platform": row.platform, "email": row.email, "results": []}
        try:
            account = _to_account(row)
            results = []
            if row.platform == "grok":
                from core.config_store import config_store
                from platforms.grok.grok2api_upload import upload_to_grok2api

                api_url = str(config_store.get("grok2api_url", "") or "").strip() or "http://127.0.0.1:8011"
                app_key = str(config_store.get("grok2api_app_key", "") or "").strip() or "grok2api"
                ok, msg = upload_to_grok2api(account, api_url=api_url, app_key=app_key)
                results.append({"name": "grok2api", "ok": ok, "msg": msg})

            elif row.platform == "chatgpt":
                from services.cliproxyapi_sync import sync_chatgpt_account_to_cliproxyapi

                ok, msg = sync_chatgpt_account_to_cliproxyapi(account)
                results.append({"name": "CLIProxyAPI", "ok": ok, "msg": msg})

            elif row.platform == "kiro":
                from core.config_store import config_store
                from platforms.kiro.account_manager_upload import upload_to_kiro_manager

                configured_path = str(config_store.get("kiro_manager_path", "") or "").strip() or None
                ok, msg = upload_to_kiro_manager(account, path=configured_path)
                results.append({"name": "Kiro Manager", "ok": ok, "msg": msg})

            if not results:
                item["results"].append({"name": "skip", "ok": False, "msg": "未配置对应导入目标"})
                summary["failed"] += 1
            else:
                item["results"] = results
                if all(r.get("ok") for r in results):
                    summary["success"] += 1
                else:
                    summary["failed"] += 1
        except Exception as e:
            item["results"].append({"name": "error", "ok": False, "msg": str(e)})
            summary["failed"] += 1
        summary["items"].append(item)
        summary["total"] += 1

    return summary
