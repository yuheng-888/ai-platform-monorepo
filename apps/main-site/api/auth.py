from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from core.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    authenticate_admin,
    bootstrap_admin,
    build_session_token,
    get_admin_state,
    get_request_username,
    set_admin_credentials,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class BootstrapRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    new_username: str = ""


def _validate_credentials_input(username: str, password: str) -> tuple[str, str]:
    username = str(username or "").strip()
    password = str(password or "")
    if not username:
        raise HTTPException(400, "用户名不能为空")
    if len(password) < 8:
        raise HTTPException(400, "密码长度至少 8 位")
    return username, password


def _set_login_cookie(response: Response, username: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        build_session_token(username),
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )


@router.get("/me")
def get_auth_me(request: Request):
    state = get_admin_state()
    username = get_request_username(request)
    return {
        "ok": True,
        "configured": state.configured,
        "authenticated": bool(username),
        "username": username,
    }


@router.post("/bootstrap")
def bootstrap_auth(body: BootstrapRequest, response: Response):
    if get_admin_state().configured:
        raise HTTPException(409, "管理员账号已初始化")
    username, password = _validate_credentials_input(body.username, body.password)
    bootstrap_admin(username, password)
    _set_login_cookie(response, username)
    return {"ok": True, "username": username}


@router.post("/login")
def login_auth(body: LoginRequest, response: Response):
    state = get_admin_state()
    if not state.configured:
        raise HTTPException(409, "管理员账号尚未初始化")
    username, password = _validate_credentials_input(body.username, body.password)
    if not authenticate_admin(username, password):
        raise HTTPException(401, "用户名或密码错误")
    _set_login_cookie(response, username)
    return {"ok": True, "username": username}


@router.post("/logout")
def logout_auth(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, request: Request, response: Response):
    current_username = get_request_username(request)
    if not current_username:
        raise HTTPException(401, "未登录")

    state = get_admin_state()
    if not verify_password(body.current_password, state.password_hash):
        raise HTTPException(401, "当前密码错误")

    next_username = str(body.new_username or "").strip() or current_username
    _, new_password = _validate_credentials_input(next_username, body.new_password)
    set_admin_credentials(next_username, new_password)
    _set_login_cookie(response, next_username)
    return {"ok": True, "username": next_username}
