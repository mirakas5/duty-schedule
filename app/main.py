"""FastAPI 엔트리 — 라우터 등록·정적 서빙·테이블 생성 (인증 없음).

Design Ref: §2.1 Component, §11.1 File Structure
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.admin.router import router as admin_router
from app.db.base import Base, engine
from app.holidays.router import router as holidays_router
from app.members.router import router as members_router
from app.scheduling.router import router as schedule_router

APP_DIR = Path(__file__).resolve().parent

# 테이블 생성(슬림 — Alembic 없이 기동 시 생성)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="NEXTRADE IT전략본부 당직표", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.include_router(admin_router)
app.include_router(members_router)
app.include_router(holidays_router)
app.include_router(schedule_router)

# 정적 자산(로컬 번들 — 외부 CDN 금지)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (APP_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
