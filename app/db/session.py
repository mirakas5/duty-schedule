"""요청 단위 DB 세션 의존성."""
from __future__ import annotations

from typing import Iterator

from sqlalchemy.orm import Session

from app.db.base import SessionLocal


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
