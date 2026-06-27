"""holidays 라우터 — 인증 가드 없음(누구나)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.holidays import service
from app.holidays.schemas import HolidayIn, HolidayOut, HolidayUpdate

router = APIRouter(prefix="/api/holidays", tags=["holidays"])


@router.get("", response_model=list[HolidayOut])
def list_holidays(year: Optional[int] = None, db: Session = Depends(get_db)):
    return service.list_holidays(db, year=year)


@router.post("", response_model=HolidayOut, status_code=201)
def create_holiday(payload: HolidayIn, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    return service.create_holiday(db, payload.date, payload.name, payload.type)


@router.put("/{hid}", response_model=HolidayOut)
def update_holiday(hid: int, payload: HolidayUpdate, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    h = service.update_holiday(db, hid, payload.date, payload.name, payload.type)
    if h is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "공휴일 없음"})
    return h


@router.delete("/{hid}")
def delete_holiday(hid: int, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    if not service.delete_holiday(db, hid):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "공휴일 없음"})
    return {"data": {"deleted": True}}
