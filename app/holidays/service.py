"""holidays 비즈니스 로직."""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Set

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.db.models import Holiday


def list_holidays(db: Session, year: Optional[int] = None) -> List[Holiday]:
    stmt = select(Holiday).order_by(Holiday.date)
    if year is not None:
        stmt = stmt.where(extract("year", Holiday.date) == year)
    return list(db.scalars(stmt))


def holiday_dates(db: Session) -> Set[date]:
    return set(db.scalars(select(Holiday.date)))


def create_holiday(db: Session, d: date, name: str, type_: str) -> Holiday:
    existing = db.scalar(select(Holiday).where(Holiday.date == d))
    if existing:
        existing.name = name
        existing.type = type_
        db.commit()
        db.refresh(existing)
        return existing
    h = Holiday(date=d, name=name, type=type_)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def update_holiday(db: Session, hid: int, d, name, type_) -> Optional[Holiday]:
    h = db.get(Holiday, hid)
    if h is None:
        return None
    if d is not None:
        h.date = d
    if name is not None:
        h.name = name
    if type_ is not None:
        h.type = type_
    db.commit()
    db.refresh(h)
    return h


def delete_holiday(db: Session, hid: int) -> bool:
    h = db.get(Holiday, hid)
    if h is None:
        return False
    db.delete(h)
    db.commit()
    return True
