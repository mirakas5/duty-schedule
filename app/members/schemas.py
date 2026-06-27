"""members 모듈 Pydantic 스키마."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class MemberOut(BaseModel):
    id: int
    name: str
    active: bool
    sort_order: int

    model_config = {"from_attributes": True}


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None


class UploadResult(BaseModel):
    total: int      # 새로 등록된 인원 수
    cleared: int    # 삭제된 기존 인원 수
