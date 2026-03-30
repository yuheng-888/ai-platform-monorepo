from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from typing import Optional
from core.db import TaskLog, engine
from core.config_store import config_store
import re
import time, json, asyncio, threading, logging

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)

_tasks: dict = {}
_tasks_lock = threading.Lock()

MAX_FINISHED_TASKS = 200
CLEANUP_THRESHOLD = 250
DEFAULT_REGISTER_MAX_CONCURRENCY = 10


def _cleanup_old_tasks():
    """Remove oldest finished tasks when the dict grows too large."""
    with _tasks_lock:
        finished = [
            (tid, t) for tid, t in _tasks.items()
            if t.get("status") in ("done", "failed")
        ]
        if len(finished) <= MAX_FINISHED_TASKS:
            return
        finished.sort(key=lambda x: x[0])
        to_remove = finished[: len(finished) - MAX_FINISHED_TASKS]
        for tid, _ in to_remove:
            del _tasks[tid]


def has_active_auto_restock_task(platform: str) -> bool:
    with _tasks_lock:
        for task in _tasks.values():
            meta = dict(task.get("meta") or {})
            if not meta.get("auto_restock"):
                continue
            if meta.get("platform") != platform:
                continue
            if task.get("status") in ("pending", "running"):
                return True
    return False


def _get_int_config(key: str, default: int) -> int:
    raw = str(config_store.get(key, "") or "").strip()
    try:
        return int(raw)
    except Exception:
        return default


def _get_register_concurrency_limit() -> int:
    return max(1, _get_int_config("register_max_concurrency", DEFAULT_REGISTER_MAX_CONCURRENCY))


def _get_effective_task_concurrency(*, requested: int, count: int) -> int:
    requested_value = max(1, int(requested or 1))
    count_value = max(1, int(count or 1))
    return min(requested_value, count_value, _get_register_concurrency_limit())


def _build_register_proxy_account(task_id: str, worker_index: int) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", str(task_id or "").strip()).strip(".-") or "task"
    return f"{base}.slot-{max(0, int(worker_index)) + 1}"


def _resolve_register_proxy(req: "RegisterTaskRequest", *, task_id: str, worker_index: int) -> Optional[str]:
    if req.proxy:
        return req.proxy
    from core.proxy_pool import proxy_pool

    return proxy_pool.get_next(
        platform=req.platform,
        purpose="register",
        account=_build_register_proxy_account(task_id, worker_index),
    )


class RegisterTaskRequest(BaseModel):
    platform: str
    email: Optional[str] = None
    password: Optional[str] = None
    count: int = 1
    concurrency: int = 1
    register_delay_seconds: float = 0
    proxy: Optional[str] = None
    executor_type: str = "protocol"
    captcha_solver: str = "yescaptcha"
    extra: dict = Field(default_factory=dict)


class TaskLogBatchDeleteRequest(BaseModel):
    ids: list[int]


def _log(task_id: str, msg: str):
    """向任务追加一条日志"""
    ts = time.strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    with _tasks_lock:
        if task_id in _tasks:
            _tasks[task_id].setdefault("logs", []).append(entry)
    print(entry)


def _save_task_log(platform: str, email: str, status: str,
                   error: str = "", detail: dict = None):
    """Write a TaskLog record to the database."""
    with Session(engine) as s:
        log = TaskLog(
            platform=platform,
            email=email,
            status=status,
            error=error,
            detail_json=json.dumps(detail or {}, ensure_ascii=False),
        )
        s.add(log)
        s.commit()


def _auto_upload_integrations(task_id: str, account):
    """注册成功后自动导入外部系统。"""
    try:
        from services.external_sync import sync_account

        for result in sync_account(account):
            name = result.get("name", "Auto Upload")
            ok = bool(result.get("ok"))
            msg = result.get("msg", "")
            _log(task_id, f"  [{name}] {'✓ ' + msg if ok else '✗ ' + msg}")
    except Exception as e:
        _log(task_id, f"  [Auto Upload] 自动导入异常: {e}")


def _run_register(task_id: str, req: RegisterTaskRequest):
    from core.registry import get
    from core.base_platform import RegisterConfig
    from core.db import save_account
    from core.base_mailbox import create_mailbox

    with _tasks_lock:
        _tasks[task_id]["status"] = "running"
    success = 0
    errors = []
    start_gate_lock = threading.Lock()
    next_start_time = time.time()

    try:
        PlatformCls = get(req.platform)

        def _build_mailbox(proxy: Optional[str]):
            from core.config_store import config_store
            merged_extra = config_store.get_all().copy()
            merged_extra.update({k: v for k, v in req.extra.items() if v is not None and v != ""})
            return create_mailbox(
                provider=merged_extra.get("mail_provider", "laoudo"),
                extra=merged_extra,
                proxy=proxy,
            )

        def _do_one(i: int):
            nonlocal next_start_time
            _proxy = None
            try:
                from core.proxy_pool import proxy_pool

                _proxy = _resolve_register_proxy(req, task_id=task_id, worker_index=i)
                if req.register_delay_seconds > 0:
                    with start_gate_lock:
                        now = time.time()
                        wait_seconds = max(0.0, next_start_time - now)
                        if wait_seconds > 0:
                            _log(task_id, f"第 {i+1} 个账号启动前延迟 {wait_seconds:g} 秒")
                            time.sleep(wait_seconds)
                        next_start_time = time.time() + req.register_delay_seconds
                from core.config_store import config_store
                merged_extra = config_store.get_all().copy()
                merged_extra.update({k: v for k, v in req.extra.items() if v is not None and v != ""})
                
                _config = RegisterConfig(
                    executor_type=req.executor_type,
                    captcha_solver=req.captcha_solver,
                    proxy=_proxy,
                    extra=merged_extra,
                )
                _mailbox = _build_mailbox(_proxy)
                _platform = PlatformCls(config=_config, mailbox=_mailbox)
                _platform._log_fn = lambda msg: _log(task_id, msg)
                if getattr(_platform, "mailbox", None) is not None:
                    _platform.mailbox._log_fn = _platform._log_fn
                with _tasks_lock:
                    _tasks[task_id]["progress"] = f"{i+1}/{req.count}"
                _log(task_id, f"开始注册第 {i+1}/{req.count} 个账号")
                if _proxy: _log(task_id, f"使用代理: {_proxy}")
                account = _platform.register(
                    email=req.email or None,
                    password=req.password,
                )
                if isinstance(account.extra, dict):
                    mail_provider = merged_extra.get("mail_provider", "")
                    if mail_provider:
                        account.extra.setdefault("mail_provider", mail_provider)
                    if mail_provider == "luckmail" and req.platform == "chatgpt":
                        mailbox_token = getattr(_mailbox, "_token", "") or ""
                        if mailbox_token:
                            account.extra.setdefault("mailbox_token", mailbox_token)
                        if merged_extra.get("luckmail_project_code"):
                            account.extra.setdefault("luckmail_project_code", merged_extra.get("luckmail_project_code"))
                        if merged_extra.get("luckmail_email_type"):
                            account.extra.setdefault("luckmail_email_type", merged_extra.get("luckmail_email_type"))
                        if merged_extra.get("luckmail_domain"):
                            account.extra.setdefault("luckmail_domain", merged_extra.get("luckmail_domain"))
                        if merged_extra.get("luckmail_base_url"):
                            account.extra.setdefault("luckmail_base_url", merged_extra.get("luckmail_base_url"))
                save_account(account)
                if _proxy: proxy_pool.report_success(_proxy)
                _log(task_id, f"✓ 注册成功: {account.email}")
                _save_task_log(req.platform, account.email, "success")
                _auto_upload_integrations(task_id, account)
                cashier_url = (account.extra or {}).get("cashier_url", "")
                if cashier_url:
                    _log(task_id, f"  [升级链接] {cashier_url}")
                    with _tasks_lock:
                        _tasks[task_id].setdefault("cashier_urls", []).append(cashier_url)
                return True
            except Exception as e:
                if _proxy: proxy_pool.report_fail(_proxy)
                _log(task_id, f"✗ 注册失败: {e}")
                _save_task_log(req.platform, req.email or "", "failed", error=str(e))
                return str(e)
            finally:
                if _proxy:
                    try:
                        proxy_pool.release_register_proxy(_proxy)
                    except Exception:
                        pass

        from concurrent.futures import ThreadPoolExecutor, as_completed
        max_workers = _get_effective_task_concurrency(requested=req.concurrency, count=req.count)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_do_one, i) for i in range(req.count)]
            for f in as_completed(futures):
                try:
                    result = f.result()
                except Exception as e:
                    _log(task_id, f"✗ 任务线程异常: {e}")
                    errors.append(str(e))
                    continue
                if result is True:
                    success += 1
                else:
                    errors.append(result)
    except Exception as e:
        _log(task_id, f"致命错误: {e}")
        with _tasks_lock:
            _tasks[task_id]["status"] = "failed"
            _tasks[task_id]["error"] = str(e)
        return

    with _tasks_lock:
        _tasks[task_id]["status"] = "done"
        _tasks[task_id]["success"] = success
        _tasks[task_id]["errors"] = errors
    _log(task_id, f"完成: 成功 {success} 个, 失败 {len(errors)} 个")
    _cleanup_old_tasks()


def start_register_task(
    req: RegisterTaskRequest,
    *,
    background_tasks: BackgroundTasks = None,
    meta: dict | None = None,
) -> str:
    task_id = f"task_{int(time.time()*1000)}"
    with _tasks_lock:
        _tasks[task_id] = {
            "id": task_id,
            "status": "pending",
            "progress": f"0/{req.count}",
            "logs": [],
            "meta": dict(meta or {}),
        }
    if background_tasks is not None:
        background_tasks.add_task(_run_register, task_id, req)
    else:
        threading.Thread(target=_run_register, args=(task_id, req), daemon=True).start()
    return task_id


@router.post("/register")
def create_register_task(
    req: RegisterTaskRequest,
    background_tasks: BackgroundTasks,
):
    mail_provider = req.extra.get("mail_provider")
    if mail_provider == "luckmail":
        platform = req.platform
        if platform in ("tavily", "openblocklabs"):
            raise HTTPException(400, f"LuckMail 渠道暂时不支持 {platform} 项目注册")
        
        mapping = {
            "trae": "trae",
            "cursor": "cursor",
            "grok": "grok",
            "kiro": "kiro",
            "chatgpt": "openai"
        }
        req.extra["luckmail_project_code"] = mapping.get(platform, platform)

    task_id = start_register_task(req=req, background_tasks=background_tasks)
    return {"task_id": task_id}


@router.get("/logs")
def get_logs(platform: str = None, page: int = 1, page_size: int = 50):
    with Session(engine) as s:
        q = select(TaskLog)
        if platform:
            q = q.where(TaskLog.platform == platform)
        q = q.order_by(TaskLog.id.desc())
        total = len(s.exec(q).all())
        items = s.exec(q.offset((page - 1) * page_size).limit(page_size)).all()
    return {"total": total, "items": items}


@router.post("/logs/batch-delete")
def batch_delete_logs(body: TaskLogBatchDeleteRequest):
    if not body.ids:
        raise HTTPException(400, "任务历史 ID 列表不能为空")

    unique_ids = list(dict.fromkeys(body.ids))
    if len(unique_ids) > 1000:
        raise HTTPException(400, "单次最多删除 1000 条任务历史")

    with Session(engine) as s:
        try:
            logs = s.exec(select(TaskLog).where(TaskLog.id.in_(unique_ids))).all()
            found_ids = {log.id for log in logs if log.id is not None}

            for log in logs:
                s.delete(log)

            s.commit()
            deleted_count = len(found_ids)
            not_found_ids = [log_id for log_id in unique_ids if log_id not in found_ids]
            logger.info("批量删除任务历史成功: %s 条", deleted_count)

            return {
                "deleted": deleted_count,
                "not_found": not_found_ids,
                "total_requested": len(unique_ids),
            }
        except Exception as e:
            s.rollback()
            logger.exception("批量删除任务历史失败")
            raise HTTPException(500, f"批量删除任务历史失败: {str(e)}")


@router.get("/{task_id}/logs/stream")
async def stream_logs(task_id: str, since: int = 0):
    """SSE 实时日志流"""
    with _tasks_lock:
        if task_id not in _tasks:
            raise HTTPException(404, "任务不存在")

    async def event_generator():
        sent = since
        while True:
            with _tasks_lock:
                logs = list(_tasks.get(task_id, {}).get("logs", []))
                status = _tasks.get(task_id, {}).get("status", "")
            while sent < len(logs):
                yield f"data: {json.dumps({'line': logs[sent]})}\n\n"
                sent += 1
            if status in ("done", "failed"):
                yield f"data: {json.dumps({'done': True, 'status': status})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{task_id}")
def get_task(task_id: str):
    with _tasks_lock:
        if task_id not in _tasks:
            raise HTTPException(404, "任务不存在")
        return _tasks[task_id]


@router.get("")
def list_tasks():
    with _tasks_lock:
        return list(_tasks.values())
