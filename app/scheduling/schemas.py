"""scheduling 모듈 Pydantic 스키마."""
from __future__ import annotations

from datetime import date as date_type
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Slot = Literal["dawn", "night"]


class GenerateIn(BaseModel):
    start_date: date_type
    end_date: Optional[date_type] = None  # 없으면 시작일+1년
    weight_total: float = 1.0
    weight_gap: float = 1.0
    reset: bool = False  # True면 기존 전체 삭제 후 생성, False면 이력 유지(이어서 생성)


class CellOut(BaseModel):
    member_id: Optional[int] = None
    member_name: Optional[str] = None


class WeekOut(BaseModel):
    id: int
    week_start: date_type
    iso_year: int
    iso_week: int
    workdays: List[date_type]
    dawn: CellOut
    night: CellOut
    version: int


class WeekPatch(BaseModel):
    slot: Slot
    member_id: Optional[int] = None  # None = 삭제(공석)
    version: int


class SwapIn(BaseModel):
    a_week_id: int
    a_slot: Slot
    b_week_id: int
    b_slot: Slot
    a_version: int
    b_version: int
