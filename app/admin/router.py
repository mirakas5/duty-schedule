"""관리 인증 라우터 — 공유 비밀번호 + IP 게이트 (개인 계정/AD 없음)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.core import security
from app.core.config import settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LoginIn(BaseModel):
    password: str


@router.get("/status")
def status(request: Request):
    return {"data": security.admin_status(request)}


@router.post("/login")
def login(payload: LoginIn, request: Request, response: Response):
    ip = security.client_ip(request)
    if not security.ip_allowed(ip):
        raise HTTPException(status_code=403, detail={"code": "ADMIN_IP_DENIED", "message": "이 PC에서는 관리 기능을 사용할 수 없습니다"})
    if not security.verify_password(payload.password):
        raise HTTPException(status_code=401, detail={"code": "ADMIN_BAD_PASSWORD", "message": "비밀번호가 올바르지 않습니다"})
    token = security.make_token()
    response.set_cookie(
        key=security.COOKIE_NAME,
        value=token,
        max_age=settings.ADMIN_TTL,
        httponly=True,
        samesite="lax",
    )
    return {"data": {"authed": True}}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(security.COOKIE_NAME)
    return {"data": {"authed": False}}
