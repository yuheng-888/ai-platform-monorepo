"""CLIProxyAPI auth pool summary for dashboard."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from sqlmodel import Session, select

from core.db import CliproxyapiRemovalEvent, engine
from services.cliproxyapi_sync import (
    DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY,
    resolve_cliproxyapi_url,
)


_DEFAULT_LOG_PATH = Path("/www/wwwroot/cpa/cliproxyapi.log")
_REMOVE_EVENT_RE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\].*auth file changed \(REMOVE\): (?P<file_name>[^,]+), processing incrementally$"
)


def _get_config_value(key: str, default: str = "") -> str:
    try:
        from core.config_store import config_store

        return str(config_store.get(key, default) or "").strip()
    except Exception:
        return default


def _management_key() -> str:
    return _get_config_value("cliproxyapi_management_key", DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY) or DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY


def _management_auth_files_url() -> str:
    base = resolve_cliproxyapi_url()
    return f"{base.rstrip('/')}/v0/management/auth-files" if base else ""


def _parse_removed_at(raw: str) -> datetime:
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _record_removal_events(log_text: str) -> int:
    inserted = 0
    with Session(engine) as session:
        for line in (log_text or "").splitlines():
            matched = _REMOVE_EVENT_RE.match(line.strip())
            if not matched:
                continue
            fingerprint = hashlib.sha1(line.encode("utf-8")).hexdigest()
            exists = session.exec(
                select(CliproxyapiRemovalEvent).where(CliproxyapiRemovalEvent.fingerprint == fingerprint)
            ).first()
            if exists:
                continue
            session.add(
                CliproxyapiRemovalEvent(
                    fingerprint=fingerprint,
                    file_name=matched.group("file_name").strip(),
                    removed_at=_parse_removed_at(matched.group("timestamp").strip()),
                    source_line=line.strip(),
                )
            )
            inserted += 1
        session.commit()
    return inserted


def _sync_removal_history(log_path: Path | None = None) -> int:
    target = Path(log_path or _DEFAULT_LOG_PATH)
    if not target.exists():
        return 0
    return _record_removal_events(target.read_text(encoding="utf-8", errors="ignore"))


def _fetch_auth_files() -> list[dict[str, Any]]:
    url = _management_auth_files_url()
    if not url:
        return []
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {_management_key()}"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json() or {}
    return list(payload.get("files") or [])


def get_cliproxyapi_pool_summary(*, log_path: Path | None = None) -> dict[str, Any]:
    _sync_removal_history(log_path=log_path)

    historical_total_banned = 0
    with Session(engine) as session:
        historical_total_banned = len(session.exec(select(CliproxyapiRemovalEvent)).all())

    try:
        files = _fetch_auth_files()
    except Exception as exc:
        return {
            "total": 0,
            "enabled": 0,
            "pending_delete_banned": 0,
            "historical_total_banned": historical_total_banned,
            "last_error": str(exc),
        }

    enabled = 0
    pending_delete_banned = 0
    by_status: dict[str, int] = {}
    for item in files:
        status = str(item.get("status") or "").strip().lower() or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        unavailable = bool(item.get("unavailable"))
        disabled = bool(item.get("disabled"))
        if status == "active" and not unavailable and not disabled:
            enabled += 1
        else:
            pending_delete_banned += 1

    return {
        "total": len(files),
        "enabled": enabled,
        "pending_delete_banned": pending_delete_banned,
        "historical_total_banned": historical_total_banned,
        "by_status": by_status,
        "last_error": "",
    }
