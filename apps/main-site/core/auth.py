"""管理员登录与会话校验。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from core.config_store import config_store


SESSION_COOKIE_NAME = "aar_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"


@dataclass
class AdminState:
    configured: bool
    username: str
    password_hash: str


def _get_config_value(key: str, default: str = "") -> str:
    return str(config_store.get(key, default) or default).strip()


def _set_config_value(key: str, value: str) -> None:
    config_store.set(key, value)


def get_admin_state() -> AdminState:
    username = _get_config_value("admin_username", "")
    password_hash = _get_config_value("admin_password_hash", "")
    return AdminState(
        configured=bool(username and password_hash),
        username=username,
        password_hash=password_hash,
    )


def ensure_session_secret() -> str:
    current = _get_config_value("app_session_secret", "")
    if current:
        return current
    generated = secrets.token_urlsafe(32)
    _set_config_value("app_session_secret", generated)
    return generated


def _password_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(ensure_session_secret(), salt="aar-session")


def hash_password(password: str, *, salt: str | None = None, iterations: int = 240000) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        resolved_salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"{PASSWORD_HASH_PREFIX}${iterations}${resolved_salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        prefix, raw_iterations, salt, digest = stored_hash.split("$", 3)
    except ValueError:
        return False
    if prefix != PASSWORD_HASH_PREFIX:
        return False
    candidate = hash_password(password, salt=salt, iterations=int(raw_iterations))
    return hmac.compare_digest(candidate, stored_hash)


def set_admin_credentials(username: str, password: str) -> None:
    _set_config_value("admin_username", username.strip())
    _set_config_value("admin_password_hash", hash_password(password))
    ensure_session_secret()


def bootstrap_admin(username: str, password: str) -> None:
    if get_admin_state().configured:
        raise ValueError("管理员账号已初始化")
    set_admin_credentials(username, password)


def authenticate_admin(username: str, password: str) -> bool:
    state = get_admin_state()
    if not state.configured:
        return False
    if username.strip() != state.username:
        return False
    return verify_password(password, state.password_hash)


def build_session_token(username: str) -> str:
    return _password_serializer().dumps({"username": username})


def read_session_username(token: str | None) -> str:
    if not token:
        return ""
    try:
        data = _password_serializer().loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return ""
    return str((data or {}).get("username") or "").strip()


def get_request_username(request: Request) -> str:
    if hasattr(request.state, "auth_username"):
        return str(request.state.auth_username or "")
    token = request.cookies.get(SESSION_COOKIE_NAME, "")
    return read_session_username(token)


def is_public_path(path: str) -> bool:
    if path.startswith("/assets/") or path.startswith("/api/auth/"):
        return True
    return path in {"/", "/favicon.ico", "/favicon.svg"}


def should_protect_path(path: str) -> bool:
    return path.startswith("/api/") or path.startswith("/gemini")


def install_auth_middleware(app) -> None:
    @app.middleware("http")
    async def admin_auth_middleware(request: Request, call_next):
        path = request.url.path or "/"
        if is_public_path(path) or not should_protect_path(path):
            return await call_next(request)

        username = get_request_username(request)
        if not username:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        request.state.auth_username = username
        return await call_next(request)
