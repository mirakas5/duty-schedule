"""관리 기능 게이트 — 비밀번호 + IP 허용목록 (표준 라이브러리만, 추가 의존성 0).

Design Ref: §7 — 관리 탭(명단/공휴일/생성)만 보호. 조회·일상 편집은 공개.
개인 계정/AD 없이 '공유 관리자 비밀번호 + 관리자 PC IP' 2중 게이트.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from app.core.config import settings

COOKIE_NAME = "admin_session"


# ── 비밀번호 ────────────────────────────────────────────────────────
def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_password(password: str) -> bool:
    # bytes 비교로 non-ASCII 비밀번호도 안전하게 처리
    if settings.ADMIN_PASSWORD_HASH:
        return hmac.compare_digest(settings.ADMIN_PASSWORD_HASH.strip().encode(), _sha256(password).encode())
    if settings.ADMIN_PASSWORD:
        return hmac.compare_digest(settings.ADMIN_PASSWORD.encode("utf-8"), password.encode("utf-8"))
    return False


# ── 서명 쿠키 토큰 ──────────────────────────────────────────────────
def _sign(payload: str) -> str:
    return hmac.new(settings.ADMIN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token() -> str:
    exp = int(time.time()) + settings.ADMIN_TTL
    payload = f"admin:{exp}"
    raw = f"{payload}:{_sign(payload)}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def verify_token(token: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        role, exp, sig = raw.split(":")
        payload = f"{role}:{exp}"
        if not hmac.compare_digest(sig, _sign(payload)):
            return False
        return int(exp) > int(time.time())
    except Exception:
        return False


# ── IP 허용목록 ─────────────────────────────────────────────────────
def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


def ip_allowed(ip: str) -> bool:
    # 미설정이면 IP 게이트 비활성(비밀번호만). 설정 시 목록 + 로컬호스트 허용.
    if not settings.ADMIN_IPS:
        return True
    return ip in settings.ADMIN_IPS or ip in ("127.0.0.1", "::1", "localhost")


# ── 의존성 ──────────────────────────────────────────────────────────
def require_admin(request: Request) -> None:
    """관리 엔드포인트 가드: IP 허용 + 유효 관리 세션 쿠키."""
    ip = client_ip(request)
    if not ip_allowed(ip):
        raise HTTPException(status_code=403, detail={"code": "ADMIN_IP_DENIED", "message": "이 PC에서는 관리 기능을 사용할 수 없습니다"})
    token = request.cookies.get(COOKIE_NAME, "")
    if not token or not verify_token(token):
        raise HTTPException(status_code=401, detail={"code": "ADMIN_REQUIRED", "message": "관리자 로그인이 필요합니다"})


def admin_status(request: Request) -> dict:
    ip = client_ip(request)
    token = request.cookies.get(COOKIE_NAME, "")
    return {"ip": ip, "ip_allowed": ip_allowed(ip), "authed": bool(token and verify_token(token))}
