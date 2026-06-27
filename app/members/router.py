"""members 라우터 — 인증 가드 없음(누구나)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.members import service
from app.members.excel import extract_names
from app.members.schemas import MemberOut, MemberUpdate, UploadResult

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("", response_model=list[MemberOut])
def list_members(active_only: bool = False, db: Session = Depends(get_db)):
    return service.list_members(db, active_only=active_only)


@router.post("/upload", response_model=UploadResult)
async def upload_members(file: UploadFile = File(...), db: Session = Depends(get_db), _: None = Depends(require_admin)):
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": ".xlsx 파일만 업로드 가능합니다"})
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB 제한
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "파일이 너무 큽니다(최대 5MB)"})
    try:
        names = extract_names(content)
    except Exception:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "엑셀을 읽을 수 없습니다"})
    if not names:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "이름을 찾지 못했습니다"})
    return service.replace_from_names(db, names)


@router.put("/{member_id}", response_model=MemberOut)
def update_member(member_id: int, payload: MemberUpdate, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    m = service.update_member(db, member_id, payload.name, payload.active)
    if m is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "멤버 없음"})
    return m


@router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    if not service.delete_member(db, member_id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "멤버 없음"})
    return {"data": {"deleted": True}}
