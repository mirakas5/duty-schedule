"""L1 API 통합 테스트 — Design §8.3 + 관리 게이트.

격리된 임시 DB로 전체 흐름(인증→업로드→생성→조회→교환→충돌→제약)을 검증.
"""
import io
import os
import tempfile

# app import 전에 환경 지정 (config가 import 시점에 읽음)
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_duty.sqlite")
os.environ["ADMIN_PASSWORD"] = "test123"
os.environ["ADMIN_SECRET"] = "test-secret"
os.environ["ADMIN_IPS"] = ""  # IP 게이트 비활성(비번만)

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(names):
    wb = Workbook()
    ws = wb.active
    ws.append(["이름"])
    for n in names:
        ws.append([n])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _login(c):
    r = c.post("/api/admin/login", json={"password": "test123"})
    assert r.status_code == 200, r.text


def test_admin_required_without_login():
    """로그인 없이 관리 엔드포인트 호출 → 401."""
    c = TestClient(app)  # 쿠키 없는 새 클라이언트
    r = c.post("/api/members/upload", files={"file": ("m.xlsx", _xlsx(["x", "y"]), XLSX_MIME)})
    assert r.status_code == 401
    r = c.post("/api/schedule/generate", json={"start_date": "2026-07-01"})
    assert r.status_code == 401
    r = c.post("/api/holidays", json={"date": "2026-08-15", "name": "광복절"})
    assert r.status_code == 401


def test_admin_bad_password():
    c = TestClient(app)
    r = c.post("/api/admin/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_public_endpoints_open_without_login():
    """조회 계열은 로그인 없이 가능."""
    c = TestClient(app)
    assert c.get("/api/schedule").status_code == 200
    assert c.get("/api/members").status_code == 200
    assert c.get("/api/holidays").status_code == 200


def test_full_flow():
    _login(client)

    # 업로드
    r = client.post("/api/members/upload", files={"file": ("m.xlsx", _xlsx(["가", "나", "다", "라", "마", "바"]), XLSX_MIME)})
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 6

    # 생성 — 총량 편차 ≤ 1
    r = client.post("/api/schedule/generate", json={"start_date": "2026-07-01"})
    assert r.status_code == 201, r.text
    assert r.json()["data"]["fairness"]["total"]["diff"] <= 1

    # 조회(공개)
    weeks = client.get("/api/schedule").json()
    assert len(weeks) >= 50

    # 드래그 교환(공개)
    a, b = weeks[0], weeks[1]
    r = client.post("/api/schedule/swap", json={
        "a_week_id": a["id"], "a_slot": "dawn",
        "b_week_id": b["id"], "b_slot": "dawn",
        "a_version": a["version"], "b_version": b["version"],
    })
    assert r.status_code == 200, r.text

    # version 충돌 → 409 (공개 편집)
    r = client.patch(f"/api/schedule/week/{a['id']}", json={"slot": "night", "member_id": None, "version": 999})
    assert r.status_code == 409

    # 우클릭 삭제(공개) → 정상
    cur = client.get("/api/schedule").json()[0]
    r = client.patch(f"/api/schedule/week/{cur['id']}", json={"slot": "night", "member_id": None, "version": cur["version"]})
    assert r.status_code == 200

    # 같은 주 새벽=야간 위반 → 400
    w = client.get("/api/schedule").json()[5]
    r = client.patch(f"/api/schedule/week/{w['id']}", json={"slot": "night", "member_id": w["dawn"]["member_id"], "version": w["version"]})
    assert r.status_code == 400


def test_upload_rejects_non_xlsx():
    _login(client)
    r = client.post("/api/members/upload", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 400
