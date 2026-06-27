"""members 비즈니스 로직."""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Member, SchedulePeriod


def list_members(db: Session, active_only: bool = False) -> List[Member]:
    stmt = select(Member).order_by(Member.sort_order, Member.id)
    if active_only:
        stmt = stmt.where(Member.active.is_(True))
    return list(db.scalars(stmt))


def replace_from_names(db: Session, names: List[str]) -> dict:
    """엑셀 명단으로 **전체 교체**. 기존 멤버를 모두 삭제하고 새로 등록한다.

    멤버를 비우면 기존 스케줄이 삭제된 멤버를 참조해 무효가 되므로, 스케줄도 함께 초기화한다.
    """
    cleared = len(list(db.scalars(select(Member))))

    # 명단 교체 → 기존 스케줄 무효 → 함께 초기화
    for p in db.scalars(select(SchedulePeriod)):
        db.delete(p)
    for m in db.scalars(select(Member)):
        db.delete(m)
    db.flush()

    for i, name in enumerate(names):
        db.add(Member(name=name, active=True, sort_order=i))
    db.commit()

    return {"total": len(names), "cleared": cleared}


def update_member(db: Session, member_id: int, name: str | None, active: bool | None) -> Member | None:
    m = db.get(Member, member_id)
    if m is None:
        return None
    if name is not None:
        m.name = name.strip()
    if active is not None:
        m.active = active
    db.commit()
    db.refresh(m)
    return m


def delete_member(db: Session, member_id: int) -> bool:
    m = db.get(Member, member_id)
    if m is None:
        return False
    db.delete(m)
    db.commit()
    return True
