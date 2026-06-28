"""scheduling 오케스트레이션 — 생성/조회/통계/교환/수정 (일 단위 저장).

Design Ref: §2.2 Data Flow, §3.5 엔진 연동
- 자동 생성: 주 단위 공정 배정(engine) → 그 주 평일 전체에 같은 사람을 '일 단위로' 펼쳐 저장.
- 수동 편집(드래그/우클릭): 하루(ScheduleDay) 단위로만 변경.
"""
from __future__ import annotations

import io
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Member, SchedulePeriod, ScheduleDay
from app.holidays.service import holiday_dates
from app.members.service import list_members
from app.scheduling import calendar as cal
from app.scheduling import engine


class ScheduleError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _week_ord_of(d: date) -> int:
    """날짜가 속한 ISO 주의 월요일 기준 절대 주차 키."""
    monday = d - timedelta(days=d.weekday())
    return cal.week_ordinal(monday)


def _active_period(db: Session) -> Optional[SchedulePeriod]:
    return db.scalar(
        select(SchedulePeriod).where(SchedulePeriod.status == "active").order_by(SchedulePeriod.id.desc())
    )


# ── 생성 (시작/종료일 + 과거 이력 시드, 일 단위 저장) ───────────────
def generate(
    db: Session,
    start_date: date,
    end_date: Optional[date] = None,
    w_total: float = 1.0,
    w_gap: float = 1.0,
    reset: bool = False,
) -> dict:
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
    new_dates = {d for w in new_weeks for d in w.workdays}

    if reset:
        for p in db.scalars(select(SchedulePeriod)):
            db.delete(p)
        db.flush()

    period = _active_period(db)
    if period is None:
        period = SchedulePeriod(start_date=start_date, end_date=end_date, weight_total=w_total, weight_gap=w_gap, status="active")
        db.add(period)
        db.flush()

    # 구간과 겹치는 기존 일자는 교체(삭제), 나머지는 이력으로 보존
    existing = list(db.scalars(select(ScheduleDay).where(ScheduleDay.period_id == period.id)))
    remaining = []
    for d in existing:
        if d.date in new_dates:
            db.delete(d)
        else:
            remaining.append(d)
    db.flush()

    # 보존 이력 → 엔진 시드(주 단위): {member_id: (배정 주수, 마지막 주차키)}
    member_weeks: dict = {}
    member_last: dict = {}
    for d in remaining:
        word = _week_ord_of(d.date)
        for mid in (d.dawn_member_id, d.night_member_id):
            if mid is None:
                continue
            member_weeks.setdefault(mid, set()).add(word)
            member_last[mid] = max(member_last.get(mid, word), word)
    initial = {mid: (len(weeks), member_last[mid]) for mid, weeks in member_weeks.items()}

    eng_members = [engine.Member(id=m.id, name=m.name, sort_order=m.sort_order) for m in members]
    week_keys = [cal.week_ordinal(w.week_start) for w in new_weeks]
    assignments = engine.assign(eng_members, week_keys, w_total, w_gap, initial=initial)

    # 주 단위 배정을 그 주 평일 전체에 '일 단위로' 펼쳐 저장
    for a, w in zip(assignments, new_weeks):
        for d in w.workdays:
            db.add(
                ScheduleDay(
                    period_id=period.id,
                    date=d,
                    iso_year=w.iso_year,
                    iso_week=w.iso_week,
                    dawn_member_id=a.dawn.id,
                    night_member_id=a.night.id,
                    version=0,
                )
            )

    all_dates = [d.date for d in remaining] + list(new_dates)
    period.start_date = min(all_dates)
    period.end_date = max(all_dates)
    period.weight_total = w_total
    period.weight_gap = w_gap
    db.commit()

    cumulative = stats(db)
    return {
        "period_id": period.id,
        "generated_weeks": len(new_weeks),
        "generated_days": len(new_dates),
        "carried_history_weeks": len(set().union(*member_weeks.values())) if member_weeks else 0,
        "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "fairness": {"total": cumulative["total"], "gap": cumulative["gap"]},
    }


# ── 조회 (일 단위) ──────────────────────────────────────────────────
def list_days(db: Session, date_from: Optional[date] = None, date_to: Optional[date] = None) -> List[dict]:
    period = _active_period(db)
    if period is None:
        return []
    stmt = select(ScheduleDay).where(ScheduleDay.period_id == period.id)
    if date_from:
        stmt = stmt.where(ScheduleDay.date >= date_from)
    if date_to:
        stmt = stmt.where(ScheduleDay.date <= date_to)
    rows = list(db.scalars(stmt.order_by(ScheduleDay.date)))

    names = {m.id: m.name for m in db.scalars(select(Member))}
    return [
        {
            "id": r.id,
            "date": r.date,
            "iso_year": r.iso_year,
            "iso_week": r.iso_week,
            "dawn": {"member_id": r.dawn_member_id, "member_name": names.get(r.dawn_member_id)},
            "night": {"member_id": r.night_member_id, "member_name": names.get(r.night_member_id)},
            "version": r.version,
        }
        for r in rows
    ]


# ── 통계 (공정성은 주 단위, 근무 일수도 함께) ───────────────────────
def stats(db: Session) -> dict:
    period = _active_period(db)
    empty = {"per_member": {}, "total": {"min": 0, "max": 0, "diff": 0}, "gap": {"mean_weeks": 0.0, "stdev": 0.0}}
    if period is None:
        return empty

    rows = list(db.scalars(select(ScheduleDay).where(ScheduleDay.period_id == period.id).order_by(ScheduleDay.date)))
    if not rows:
        return empty
    names = {m.id: m.name for m in db.scalars(select(Member))}

    week_set: dict = {}      # mid -> set(week ord)
    day_count: dict = {}     # mid -> 총 근무일
    dawn_days: dict = {}
    night_days: dict = {}
    for r in rows:
        word = _week_ord_of(r.date)
        for mid, slot in ((r.dawn_member_id, "dawn"), (r.night_member_id, "night")):
            if mid is None:
                continue
            week_set.setdefault(mid, set()).add(word)
            day_count[mid] = day_count.get(mid, 0) + 1
            if slot == "dawn":
                dawn_days[mid] = dawn_days.get(mid, 0) + 1
            else:
                night_days[mid] = night_days.get(mid, 0) + 1

    weeks_per = {mid: len(w) for mid, w in week_set.items()}
    vals = list(weeks_per.values())
    lo, hi = (min(vals), max(vals)) if vals else (0, 0)

    gaps: List[int] = []
    for mid, ws in week_set.items():
        ordered = sorted(ws)
        gaps.extend(ordered[i] - ordered[i - 1] for i in range(1, len(ordered)))
    if gaps:
        mean = sum(gaps) / len(gaps)
        stdev = (sum((g - mean) ** 2 for g in gaps) / len(gaps)) ** 0.5
    else:
        mean = stdev = 0.0

    per_member = {
        mid: {
            "name": names.get(mid, f"#{mid}"),
            "weeks": weeks_per.get(mid, 0),
            "days": day_count.get(mid, 0),
            "dawn": dawn_days.get(mid, 0),
            "night": night_days.get(mid, 0),
        }
        for mid in week_set
    }
    return {
        "per_member": per_member,
        "total": {"min": lo, "max": hi, "diff": hi - lo},
        "gap": {"mean_weeks": round(mean, 2), "stdev": round(stdev, 2)},
    }


# ── 편집: 수정/삭제 (우클릭/클릭) — 하루 단위 ───────────────────────
def patch_day(db: Session, day_id: int, slot: str, member_id: Optional[int], version: int) -> dict:
    d = db.get(ScheduleDay, day_id)
    if d is None:
        raise ScheduleError("NOT_FOUND", "해당 날짜 없음", 404)
    if d.version != version:
        raise ScheduleError("VERSION_CONFLICT", "스케줄이 변경됨, 새로고침 해주세요", 409)
    if member_id is not None and db.get(Member, member_id) is None:
        raise ScheduleError("VALIDATION_ERROR", "존재하지 않는 멤버", 400)

    other = d.night_member_id if slot == "dawn" else d.dawn_member_id
    if member_id is not None and other is not None and member_id == other:
        raise ScheduleError("VALIDATION_ERROR", "같은 날 새벽/야간은 서로 다른 사람이어야 합니다", 400)

    if slot == "dawn":
        d.dawn_member_id = member_id
    else:
        d.night_member_id = member_id
    d.version += 1
    db.commit()
    return {"id": d.id, "version": d.version}


# ── 편집: 교환 (드래그앤드롭) — 하루 단위 ───────────────────────────
def swap(db: Session, a_day_id: int, a_slot: str, b_day_id: int, b_slot: str, a_version: int, b_version: int) -> dict:
    da = db.get(ScheduleDay, a_day_id)
    db_ = db.get(ScheduleDay, b_day_id)
    if da is None or db_ is None:
        raise ScheduleError("NOT_FOUND", "해당 날짜 없음", 404)
    if da.version != a_version or db_.version != b_version:
        raise ScheduleError("VERSION_CONFLICT", "스케줄이 변경됨, 새로고침 해주세요", 409)

    def get_slot(x, slot):
        return x.dawn_member_id if slot == "dawn" else x.night_member_id

    def set_slot(x, slot, mid):
        if slot == "dawn":
            x.dawn_member_id = mid
        else:
            x.night_member_id = mid

    ma, mb = get_slot(da, a_slot), get_slot(db_, b_slot)
    set_slot(da, a_slot, mb)
    set_slot(db_, b_slot, ma)

    for x in {da, db_}:
        if x.dawn_member_id is not None and x.dawn_member_id == x.night_member_id:
            raise ScheduleError("VALIDATION_ERROR", "교환 결과 같은 날 새벽/야간이 동일해집니다", 400)

    da.version += 1
    if db_ is not da:
        db_.version += 1
    db.commit()
    return {"swapped": True}


# ── 내보내기 (일 단위) ──────────────────────────────────────────────
def export_xlsx(db: Session) -> bytes:
    from openpyxl import Workbook

    days = list_days(db)
    dow = ["월", "화", "수", "목", "금", "토", "일"]
    wb = Workbook()
    ws = wb.active
    ws.title = "당직표"
    ws.append(["날짜", "요일", "새벽근무", "야간근무"])
    for d in days:
        ws.append([
            d["date"].isoformat(),
            dow[d["date"].weekday()],
            d["dawn"]["member_name"] or "",
            d["night"]["member_name"] or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
