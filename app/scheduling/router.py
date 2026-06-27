"""scheduling 라우터 — 인증 가드 없음(누구나)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.scheduling import service
from app.scheduling.schemas import GenerateIn, SwapIn, WeekOut, WeekPatch

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


def _raise(e: service.ScheduleError):
    raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})


@router.post("/generate", status_code=201)
def generate(payload: GenerateIn, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    try:
        data = service.generate(
            db, payload.start_date, payload.end_date,
            payload.weight_total, payload.weight_gap, payload.reset,
        )
    except service.ScheduleError as e:
        _raise(e)
    return {"data": data}


@router.get("", response_model=list[WeekOut])
def list_weeks(date_from: Optional[date] = None, date_to: Optional[date] = None, db: Session = Depends(get_db)):
    return service.list_weeks(db, date_from, date_to)


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return {"data": service.stats(db)}


@router.patch("/week/{week_id}")
def patch_week(week_id: int, payload: WeekPatch, db: Session = Depends(get_db)):
    try:
        data = service.patch_cell(db, week_id, payload.slot, payload.member_id, payload.version)
    except service.ScheduleError as e:
        _raise(e)
    return {"data": data}


@router.post("/swap")
def swap(payload: SwapIn, db: Session = Depends(get_db)):
    try:
        data = service.swap(
            db, payload.a_week_id, payload.a_slot, payload.b_week_id, payload.b_slot,
            payload.a_version, payload.b_version,
        )
    except service.ScheduleError as e:
        _raise(e)
    return {"data": data}


@router.get("/export")
def export(db: Session = Depends(get_db)):
    content = service.export_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="duty_schedule.xlsx"'},
    )
