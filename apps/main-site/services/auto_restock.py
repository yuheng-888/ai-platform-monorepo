"""自动补货逻辑。"""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from core.config_store import config_store
from core.db import AccountModel, engine


AVAILABLE_RESTOCK_STATUSES = ("registered", "trial", "subscribed")


def _get_bool(key: str, default: bool = False) -> bool:
    raw = str(config_store.get(key, "") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _get_int(key: str, default: int) -> int:
    raw = str(config_store.get(key, "") or "").strip()
    try:
        return int(raw)
    except Exception:
        return default


def _get_str(key: str, default: str = "") -> str:
    return str(config_store.get(key, default) or default).strip()


def _get_default_restock_concurrency() -> int:
    return max(1, _get_int("register_max_concurrency", 10))


def get_chatgpt_available_inventory() -> int:
    with Session(engine) as s:
        rows = s.exec(
            select(AccountModel).where(
                AccountModel.platform == "chatgpt",
                AccountModel.status.in_(AVAILABLE_RESTOCK_STATUSES),
            )
        ).all()
    return len(rows)


def get_chatgpt_restock_summary() -> dict[str, Any]:
    from api.tasks import has_active_auto_restock_task

    return {
        "available": get_chatgpt_available_inventory(),
        "enabled": _get_bool("chatgpt_auto_restock_enabled", False),
        "threshold": _get_int("chatgpt_auto_restock_threshold", 0),
        "target": _get_int("chatgpt_auto_restock_target", 0),
        "batch_size": _get_int("chatgpt_auto_restock_batch_size", 1),
        "concurrency": max(1, _get_int("chatgpt_auto_restock_concurrency", _get_default_restock_concurrency())),
        "proxy": _get_str("chatgpt_auto_restock_proxy", ""),
        "executor_type": _get_str("chatgpt_auto_restock_executor_type", "protocol") or "protocol",
        "captcha_solver": _get_str("chatgpt_auto_restock_captcha_solver", "yescaptcha") or "yescaptcha",
        "has_active_task": has_active_auto_restock_task("chatgpt"),
    }


def check_and_trigger_chatgpt_auto_restock() -> dict[str, Any]:
    from api.tasks import RegisterTaskRequest, has_active_auto_restock_task, start_register_task

    enabled = _get_bool("chatgpt_auto_restock_enabled", False)
    threshold = max(0, _get_int("chatgpt_auto_restock_threshold", 0))
    target = max(threshold, _get_int("chatgpt_auto_restock_target", threshold))
    batch_size = max(1, _get_int("chatgpt_auto_restock_batch_size", 1))
    concurrency = max(1, _get_int("chatgpt_auto_restock_concurrency", _get_default_restock_concurrency()))
    available = get_chatgpt_available_inventory()

    if not enabled:
        return {"triggered": False, "reason": "disabled", "available": available, "count": 0}

    if available >= threshold:
        return {"triggered": False, "reason": "threshold_met", "available": available, "count": 0}

    if has_active_auto_restock_task("chatgpt"):
        return {"triggered": False, "reason": "active_task", "available": available, "count": 0}

    deficit = max(target - available, 1)
    count = max(1, min(batch_size, deficit))
    req = RegisterTaskRequest(
        platform="chatgpt",
        count=count,
        concurrency=concurrency,
        proxy=_get_str("chatgpt_auto_restock_proxy", "") or None,
        executor_type=_get_str("chatgpt_auto_restock_executor_type", "protocol") or "protocol",
        captcha_solver=_get_str("chatgpt_auto_restock_captcha_solver", "yescaptcha") or "yescaptcha",
        extra={},
    )
    task_id = start_register_task(
        req=req,
        meta={
            "auto_restock": True,
            "platform": "chatgpt",
            "source": "scheduler",
            "reason": "low_inventory",
        },
    )
    return {
        "triggered": True,
        "reason": "started",
        "available": available,
        "count": count,
        "task_id": task_id,
    }
