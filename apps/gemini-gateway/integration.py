from __future__ import annotations

import importlib
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fastapi import FastAPI

from embedded.gemini_business2api.paths import STATIC_DIR, ensure_data_dirs, sqlite_path_for


GEMINI_MOUNT_PATH = "/gemini"
ConfigGetter = Callable[[str, str], str]


@dataclass
class GeminiRuntimeConfig:
    mount_path: str
    data_dir: str
    sqlite_path: str
    admin_key: str
    session_secret: str


def _config_getter(default: str = "") -> ConfigGetter:
    from core.config_store import config_store

    def get_value(key: str, fallback: str = default) -> str:
        try:
            return str(config_store.get(key, fallback) or fallback)
        except Exception:
            return fallback

    return get_value


def _config_setter() -> Callable[[str, str], None]:
    from core.config_store import config_store

    def set_value(key: str, value: str) -> None:
        try:
            config_store.set(key, value)
        except Exception:
            pass

    return set_value


def _ensure_secret(
    key: str,
    config_getter: ConfigGetter,
    config_setter: Callable[[str, str], None] | None,
) -> str:
    current = str(config_getter(key, "") or "").strip()
    if current:
        return current

    generated = secrets.token_urlsafe(32)
    if config_setter is not None:
        config_setter(key, generated)
    return generated


def ensure_gemini_runtime_env(
    base_data_dir: str | os.PathLike[str] | None = None,
    config_getter: ConfigGetter | None = None,
    config_setter: Callable[[str, str], None] | None = None,
) -> GeminiRuntimeConfig:
    config_getter = config_getter or _config_getter()
    config_setter = config_setter or _config_setter()

    admin_key = _ensure_secret("gemini_admin_key", config_getter, config_setter)
    session_secret = _ensure_secret("gemini_session_secret", config_getter, config_setter)
    data_dir = ensure_data_dirs(base_data_dir)
    sqlite_path = sqlite_path_for(data_dir)

    os.environ["ADMIN_KEY"] = admin_key
    os.environ["SESSION_SECRET_KEY"] = session_secret
    os.environ["GEMINI_BUSINESS2API_DATA_DIR"] = str(data_dir)
    os.environ["SQLITE_PATH"] = str(sqlite_path)
    os.environ.setdefault("GEMINI_BUSINESS2API_GIT_SHA", "")

    return GeminiRuntimeConfig(
        mount_path=GEMINI_MOUNT_PATH,
        data_dir=str(data_dir),
        sqlite_path=str(sqlite_path),
        admin_key=admin_key,
        session_secret=session_secret,
    )


def build_gemini_subapp(
    base_data_dir: str | os.PathLike[str] | None = None,
    config_getter: ConfigGetter | None = None,
    config_setter: Callable[[str, str], None] | None = None,
):
    ensure_gemini_runtime_env(
        base_data_dir=base_data_dir,
        config_getter=config_getter,
        config_setter=config_setter,
    )
    module = importlib.import_module("embedded.gemini_business2api.main")
    return module.app


def gemini_ui_available(static_dir: Path = STATIC_DIR) -> bool:
    return (static_dir / "index.html").exists()


def get_gemini_status(
    config_getter: ConfigGetter | None = None,
):
    config_getter = config_getter or _config_getter()
    from embedded.gemini_business2api.core.version import get_version_info

    admin_key = str(
        config_getter("gemini_admin_key", "")
        or os.getenv("ADMIN_KEY", "")
        or ""
    ).strip()
    session_secret = str(
        config_getter("gemini_session_secret", "")
        or os.getenv("SESSION_SECRET_KEY", "")
        or ""
    ).strip()
    version = get_version_info()
    return {
        "name": "gemini-business2api",
        "mount_path": GEMINI_MOUNT_PATH,
        "ui_path": f"{GEMINI_MOUNT_PATH}/",
        "ui_available": gemini_ui_available(),
        "health_path": f"{GEMINI_MOUNT_PATH}/health",
        "api_base_path": f"{GEMINI_MOUNT_PATH}/v1",
        "running": True,
        "admin_key_configured": bool(admin_key),
        "session_secret_configured": bool(session_secret),
        "version": version.get("version", ""),
        "commit": version.get("commit", ""),
    }


def mount_gemini_subapp(
    app: FastAPI,
    base_data_dir: str | os.PathLike[str] | None = None,
    config_getter: ConfigGetter | None = None,
    config_setter: Callable[[str, str], None] | None = None,
) -> FastAPI:
    gemini_app = build_gemini_subapp(
        base_data_dir=base_data_dir,
        config_getter=config_getter,
        config_setter=config_setter,
    )
    app.mount(GEMINI_MOUNT_PATH, gemini_app)
    return app
