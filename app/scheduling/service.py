"""scheduling 오케스트레이션 — 생성/조회/통계/교환/수정.

Design Ref: §2.2 Data Flow, §3.5 엔진 연동
순수 엔진(engine)·캘린더(calendar)를 호출해 결과를 DB에 영속화한다.
"""
from __future__ import annotations

import io
import json
from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Member, SchedulePeriod, ScheduleWeek
from app.holidays.service import holiday_dates
from app.members.service import list_members
from app.scheduling import calendar as cal
from app.scheduling import engine


class ScheduleError(Exception):
    """검증/충돌 등 도메인 에러. code로 구분."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


# ── 생성 (시작/종료일 + 과거 이력 시드) ─────────────────────────────
def generate(
    db: Session,
    start_date: date,
    end_date: Optional[date] = None,
    w_total: float = 1.0,
    w_gap: float = 1.0,
    reset: bool = False,
) -> dict:
    """[start_date, end_date] 구간의 당직을 생성한다.

    Design Ref: FR-05/05b — reset=False(기본)이면 구간 밖의 기존 이력을 시드로 삼아
    누적 형평성(횟수·간격)을 잇는다. 구간과 겹치는 기존 주차는 새로 교체한다.
    """
    if end_date is None:
        end_date = cal.one_year_end(start_date)
    if end_date < start_date:
        raise ScheduleError("VALIDATION_ERROR", "종료일이 시작일보다 빠릅니다", 400)

    members = list_members(db, active_only=True)
    if len(members) < 2:
        raise ScheduleError("VALIDATION_ERROR", "활성 멤버가 2명 이상 필요합니다", 400)

    holidays = holiday_dates(db)
    new_weeks = cal.build_weeks(start_date, end_date, holidays)
    if not new_weeks:
        raise ScheduleError("VALIDATION_ERROR", "생성할 평일이 없습니다", 400)
    new_starts = {w.week_start for w in new_weeks}

    # reset이면 전체 초기화, 아니면 단일 active period 유지
    if reset:
        for p in db.scalars(select(SchedulePeriod)):
            db.delete(p)
        db.flush()

    period = _active_period(db)
    if period is None:
        period = SchedulePeriod(start_date=start_date, end_date=end_date, weight_total=w_total, weight_gap=w_gap, status="active")
        db.add(period)
        db.flush()

    # 구간과 겹치는 기존 주차는 교체(삭제), 나머지는 이력으로 보존
    existing = list(db.scalars(select(ScheduleWeek).where(ScheduleWeek.period_id == period.id)))
    remaining = []
    for w in existing:
        if w.week_start in new_starts:
            db.delete(w)
        else:
            remaining.append(w)
    db.flush()

    # 보존 이력 → 엔진 시드 {member_id: (누적횟수, 마지막 주차키)}
    initial: dict = {}
    for w in remaining:
        key = cal.week_ordinal(w.week_start)
        for mid in (w.dawn_member_id, w.night_member_id):
            if mid is None:
                continue
            tot, last = initial.get(mid, (0, key))
            initial[mid] = (tot + 1, max(last, key))

    eng_members = [engine.Member(id=m.id, name=m.name, sort_order=m.sort_order) for m in members]
    week_keys = [cal.week_ordinal(w.week_start) for w in new_weeks]
    assignments = engine.assign(eng_members, week_keys, w_total, w_gap, initial=initial)

    for a, w in zip(assignments, new_weeks):
        db.add(
            ScheduleWeek(
                period_id=period.id,
                week_start=w.week_start,
                iso_year=w.iso_year,
                iso_week=w.iso_week,
                workdays_json=json.dumps([d.isoformat() for d in w.workdays]),
                dawn_member_id=a.dawn.id,
                night_member_id=a.night.id,
                version=0,
            )
        )

    # period 기간을 전체 주차로 확장
    all_starts = [w.week_start for w in remaining] + list(new_starts)
    period.start_date = min(all_starts)
    period.end_date = max(max(w.workdays) for w in new_weeks) if not remaining else max(end_date, period.end_date)
    period.weight_total = w_total
    period.weight_gap = w_gap
    db.commit()

    cumulative = stats(db)
    return {
        "period_id": period.id,
        "generated_weeks": len(new_weeks),
        "generated_workdays": sum(len(w.workdays) for w in new_weeks),
        "carried_history_weeks": len(remaining),
        "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "fairness": {"total": cumulative["total"], "gap": cumulative["gap"]},
    }


# ── 조회 ────────────────────────────────────────────────────────────
def _active_period(db: Session) -> Optional[SchedulePeriod]:
    return db.scalar(
        select(SchedulePeriod).where(SchedulePeriod.status == "active").order_by(SchedulePeriod.id.desc())
    )


def list_weeks(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[dict]:
    period = _active_period(db)
    if period is None:
        return []
    stmt = select(ScheduleWeek).where(ScheduleWeek.period_id == period.id).order_by(ScheduleWeek.week_start)
    rows = list(db.scalars(stmt))

    names = {m.id: m.name for m in db.scalars(select(Member))}
    out: List[dict] = []
    for w in rows:
        workdays = [date.fromisoformat(s) for s in json.loads(w.workdays_json)]
        if date_from and date_to:
            # 그 주의 평일이 요청 구간과 겹치는 경우만
            if not any(date_from <= d <= date_to for d in workdays):
                continue
        out.append(
            {
                "id": w.id,
                "week_start": w.week_start,
                "iso_year": w.iso_year,
                "iso_week": w.iso_week,
                "workdays": workdays,
                "dawn": {"member_id": w.dawn_member_id, "member_name": names.get(w.dawn_member_id)},
                "night": {"member_id": w.night_member_id, "member_name": names.get(w.night_member_id)},
                "version": w.version,
            }
        )
    return out


# ── 통계 ────────────────────────────────────────────────────────────
def stats(db: Session) -> dict:
    period = _active_period(db)
    if period is None:
        return {"per_member": {}, "total": {"min": 0, "max": 0, "diff": 0}, "gap": {"mean_weeks": 0.0, "stdev": 0.0}}

    rows = list(
        db.scalars(
            select(ScheduleWeek).where(ScheduleWeek.period_id == period.id).order_by(ScheduleWeek.week_start)
        )
    )
    names = {m.id: m.name for m in db.scalars(select(Member))}

    counts: dict = {}
    dawn: dict = {}
    night: dict = {}
    last_idx: dict = {}
    gaps: List[int] = []

    for idx, w in enumerate(rows):
        for mid, slot in ((w.dawn_member_id, "dawn"), (w.night_member_id, "night")):
            if mid is None:
                continue
            counts[mid] = counts.get(mid, 0) + 1
            if slot == "dawn":
                dawn[mid] = dawn.get(mid, 0) + 1
            else:
                night[mid] = night.get(mid, 0) + 1
            if mid in last_idx:
                gaps.append(idx - last_idx[mid])
            last_idx[mid] = idx

    totals = list(counts.values())
    lo, hi = (min(totals), max(totals)) if totals else (0, 0)
    if gaps:
        mean = sum(gaps) / len(gaps)
        var = sum((g - mean) ** 2 for g in gaps) / len(gaps)
        stdev = var ** 0.5
    else:
        mean = stdev = 0.0

    per_member = {
        mid: {
            "name": names.get(mid, f"#{mid}"),
            "total": counts.get(mid, 0),
            "dawn": dawn.get(mid, 0),
            "night": night.get(mid, 0),
        }
        for mid in counts
    }
    return {
        "per_member": per_member,
        "total": {"min": lo, "max": hi, "diff": hi - lo},
        "gap": {"mean_weeks": round(mean, 2), "stdev": round(stdev, 2)},
    }


# ── 편집: 수정/삭제 (우클릭) ────────────────────────────────────────
def patch_cell(db: Session, week_id: int, slot: str, member_id: Optional[int], version: int) -> dict:
    w = db.get(ScheduleWeek, week_id)
    if w is None:
        raise ScheduleError("NOT_FOUND", "주차 없음", 404)
    if w.version != version:
        raise ScheduleError("VERSION_CONFLICT", "스케줄이 변경됨, 새로고침 해주세요", 409)

    if member_id is not None and db.get(Member, member_id) is None:
        raise ScheduleError("VALIDATION_ERROR", "존재하지 않는 멤버", 400)

    other = w.night_member_id if slot == "dawn" else w.dawn_member_id
    if member_id is not None and other is not None and member_id == other:
        raise ScheduleError("VALIDATION_ERROR", "같은 주의 새벽/야간은 서로 다른 사람이어야 합니다", 400)

    if slot == "dawn":
        w.dawn_member_id = member_id
    else:
        w.night_member_id = member_id
    w.version += 1
    db.commit()
    return {"id": w.id, "version": w.version}


# ── 편집: 교환 (드래그앤드롭) ───────────────────────────────────────
def swap(db: Session, a_week_id: int, a_slot: str, b_week_id: int, b_slot: str, a_version: int, b_version: int) -> dict:
    wa = db.get(ScheduleWeek, a_week_id)
    wb = db.get(ScheduleWeek, b_week_id)
    if wa is None or wb is None:
        raise ScheduleError("NOT_FOUND", "주차 없음", 404)
    if wa.version != a_version or wb.version != b_version:
        raise ScheduleError("VERSION_CONFLICT", "스케줄이 변경됨, 새로고침 해주세요", 409)

    def get_slot(w, slot):
        return w.dawn_member_id if slot == "dawn" else w.night_member_id

    def set_slot(w, slot, mid):
        if slot == "dawn":
            w.dawn_member_id = mid
        else:
            w.night_member_id = mid

    ma = get_slot(wa, a_slot)
    mb = get_slot(wb, b_slot)
    set_slot(wa, a_slot, mb)
    set_slot(wb, b_slot, ma)

    # 같은 주 내 새벽=야간 위반 검사
    for w in {wa, wb}:
        if w.dawn_member_id is not None and w.dawn_member_id == w.night_member_id:
            raise ScheduleError("VALIDATION_ERROR", "교환 결과 같은 주에 새벽/야간이 동일해집니다", 400)

    wa.version += 1
    if wb is not wa:
        wb.version += 1
    db.commit()
    return {"swapped": True}


# ── 내보내기 ────────────────────────────────────────────────────────
def export_xlsx(db: Session) -> bytes:
    from openpyxl import Workbook

    weeks = list_weeks(db)
    wb = Workbook()
    ws = wb.active
    ws.title = "당직표"
    ws.append(["주 시작일", "ISO주차", "새벽근무", "야간근무", "당직 평일수"])
    for w in weeks:
        ws.append([
            w["week_start"].isoformat(),
            f"{w['iso_year']}-W{w['iso_week']:02d}",
            w["dawn"]["member_name"] or "",
            w["night"]["member_name"] or "",
            len(w["workdays"]),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
