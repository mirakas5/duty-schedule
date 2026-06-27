"""SQLAlchemy 엔진/세션/Base 정의."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False},  # SQLite + FastAPI 멀티스레드
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass
