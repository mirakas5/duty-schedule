"""holidays 모듈 Pydantic 스키마."""
from __future__ import annotations

from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel


class HolidayIn(BaseModel):
    date: date_type
    name: str = ""
    type: str = "national"  # national | temporary | company


class HolidayUpdate(BaseModel):
    date: Optional[date_type] = None
    name: Optional[str] = None
    type: Optional[str] = None


class HolidayOut(BaseModel):
    id: int
    date: date_type
    name: str
    type: str

    model_config = {"from_attributes": True}
