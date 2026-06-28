"""DB 모델 — Design §3.1 (users/swap_requests 없음: 인증·승인 제거).

Design Ref: §3 Data Model
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Member(Base):
    """당직 대상 인원(엑셀 추출)."""
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Holiday(Base):
    """공휴일/지정일 — 관리 없이 누구나 수동 등록."""
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="national")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SchedulePeriod(Base):
    """1년 단위 생성 묶음."""
    __tablename__ = "schedule_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_total: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    weight_gap: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    days: Mapped[list["ScheduleDay"]] = relationship(
        back_populates="period", cascade="all, delete-orphan"
    )


class ScheduleDay(Base):
    """일(日) 단위 배정. 자동 생성은 주 단위로 같은 사람을 그 주 평일 전체에 채우지만,
    저장·편집은 하루 단위 → 드래그/수정이 하루만 바뀐다."""
    __tablename__ = "schedule_days"
    __table_args__ = (
        UniqueConstraint("period_id", "date", name="uq_period_date"),
        CheckConstraint(
            "dawn_member_id IS NULL OR night_member_id IS NULL "
            "OR dawn_member_id <> night_member_id",
            name="ck_day_dawn_ne_night",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("schedule_periods.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    iso_year: Mapped[int] = mapped_column(Integer, nullable=False)
    iso_week: Mapped[int] = mapped_column(Integer, nullable=False)
    dawn_member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("members.id"), nullable=True)
    night_member_id: Mapped[Optional[int]] = mapped_column(ForeignKey("members.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    period: Mapped["SchedulePeriod"] = relationship(back_populates="days")
    dawn_member: Mapped[Optional["Member"]] = relationship(foreign_keys=[dawn_member_id])
    night_member: Mapped[Optional["Member"]] = relationship(foreign_keys=[night_member_id])
