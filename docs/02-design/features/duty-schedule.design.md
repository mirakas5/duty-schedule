---
template: design
version: 1.3
feature: duty-schedule
date: 2026-06-26
author: mirakas (IT전략본부)
project: NEXTRADE IT전략본부 당직표
version_project: 0.1
status: Draft
---

# duty-schedule (NEXTRADE IT전략본부 당직표) Design Document

> **Summary**: 명단 엑셀 업로드 → 평일 1년치 새벽/야간 근무를 공정 배정(총량+간격)하고, **인증 없이 누구나** 드래그앤드롭 교환·우클릭 수정/삭제로 편집하는 단일 FastAPI+SQLite 서비스.
>
> **Project**: NEXTRADE IT전략본부 당직표
> **Version**: 0.1 · **Author**: mirakas · **Date**: 2026-06-26 · **Status**: Draft
> **Planning Doc**: [duty-schedule.plan.md](../../01-plan/features/duty-schedule.plan.md)

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 수기 당직 편성의 시간 소모와 인원 간 형평성 문제 해소 |
| **WHO** | IT전략본부 임직원 누구나(권한 구분·로그인 없음) |
| **RISK** | 폐쇄망(외부 호출 0) + 공정 분배 형평성 + 인증 없는 자유 편집의 실수/충돌 |
| **SUCCESS** | 1년 자동 생성, 편차 ≤1 + 간격 균일, 드래그/우클릭 편집 동작, 외부호출 0 |
| **SCOPE** | 기반 → 명단/공휴일 → 배정 엔진 → 편집 UI(드래그·우클릭) → 배포 |

---

## 1. Overview

### 1.1 Design Goals

- 공정 배정 로직(FR-05/05b)을 **순수 모듈(`scheduling/engine.py`)** 로 격리해 단위 테스트로 검증.
- 폐쇄망에서 **외부 호출 0건** — 모든 정적 자산 로컬 번들.
- **인증/세션 전무**: 슬림한 단일 페이지 + 직접 편집(드래그/우클릭).
- 서버(SQLite) 단일 공유 데이터로 전사 동일 당직표.

### 1.2 Design Principles

- **Pure Core**: 배정 엔진은 DB/HTTP 비의존 순수 함수.
- **Feature Modules**: members / scheduling / holidays 응집(인증·교환승인 모듈 없음).
- **No Auth, Optimistic Concurrency**: 권한 없음 + version 컬럼으로 동시 편집 충돌만 방지.
- **Offline-first**: 외부 CDN/폰트/API 금지.

---

## 2. Architecture (Option C — Pragmatic, 인증 제거 슬림판)

### 2.1 Component Diagram

```
┌──────────────────────────────┐     ┌────────────────────────────────┐     ┌──────────────┐
│  Browser (Vanilla JS, SPA)   │     │       FastAPI (단일 서비스)        │     │   SQLite     │
│  - 캘린더 조회                 │     │  Presentation: routers, static   │     │  duty.sqlite │
│  - 드래그앤드롭 교환            │────▶│  Application:  *_service.py      │────▶│  (공유 데이터) │
│  - 우클릭 수정/삭제            │ HTTP│  Domain:       engine, calendar  │     │              │
│  - 명단/공휴일/생성(누구나)     │◀────│  Infra:        db, excel         │◀────│              │
└──────────────────────────────┘     └────────────────────────────────┘     └──────────────┘
          (로그인/세션/권한 없음)
```

### 2.2 Data Flow

**스케줄 생성**
```
엑셀 업로드 → 이름 추출(openpyxl) → members upsert
[생성] → start_date + 공휴일 로드 → calendar.weekdays() → 주차 그룹화
      → engine.assign(members, weeks, weights) → schedule_weeks 저장 → 통계 응답
```

**편집 (인증 없음, 즉시 반영)**
```
드래그앤드롭: 셀 A(week,slot) → 셀 B(week,slot) drop
            → POST /api/schedule/swap → 트랜잭션[version 확인 → 두 셀 member_id 교환] → 즉시 반영
우클릭 수정:  셀 → 컨텍스트 메뉴 → 담당자 선택 → PATCH /week/{id} {slot, member_id}
우클릭 삭제:  셀 → 컨텍스트 메뉴 → 삭제 → PATCH /week/{id} {slot, member_id:null}(공석)
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `scheduling/service` | `engine`, `calendar`, `db` | 생성·편집·교환 영속화 |
| `scheduling/engine` | (없음 — 순수) | 공정 배정 알고리즘 |
| `members/service` | `excel`, `db` | 명단 추출·관리 |
| `holidays/service` | `db` | 공휴일 CRUD |
| 외부 라이브러리 | `fastapi`, `uvicorn`, `sqlalchemy`, `openpyxl`, `pydantic`, `pydantic-settings`, `python-multipart` | (※ ldap3·itsdangerous 제거) |

---

## 3. Data Model

### 3.1 Entity Definition (SQLAlchemy) — users 테이블 없음

```python
# app/db/models.py (요약)

class Member(Base):         # 당직 풀(엑셀 추출)
    id: int (PK)
    name: str
    active: bool = True
    sort_order: int
    created_at: datetime

class Holiday(Base):        # 공휴일/지정일(수동)
    id: int (PK)
    date: date (unique)
    name: str
    type: str               # 'national'|'temporary'|'company'
    created_at: datetime

class SchedulePeriod(Base): # 생성 단위(1년)
    id: int (PK)
    start_date: date
    end_date: date
    weight_total: float
    weight_gap: float
    status: str             # 'active'|'archived'
    generated_at: datetime

class ScheduleWeek(Base):   # 주 단위 배정(고정)
    id: int (PK)
    period_id: int (FK schedule_periods.id)
    week_start: date        # 월요일
    iso_year: int
    iso_week: int
    workdays_json: str      # 그 주 실제 당직 평일(공휴일 제외)
    dawn_member_id: int | None (FK members.id)
    night_member_id: int | None (FK members.id)
    version: int = 0        # 낙관적 락(동시 편집 충돌 방지)
    created_at, updated_at: datetime
    # CHECK: dawn_member_id != night_member_id (둘 다 NULL 아닐 때)

# (선택) class ChangeLog: 편집 추적용 — action/week_id/before/after/at. 슬림 1차엔 생략 가능.
```

### 3.2 Entity Relationships

```
[Member] 1 ──── N [ScheduleWeek.dawn/night]
[SchedulePeriod] 1 ──── N [ScheduleWeek]
[Holiday]  (독립, 생성 시 평일 계산에 참조)
```

### 3.3 Database Schema (핵심)

```sql
CREATE TABLE schedule_weeks (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  period_id     INTEGER NOT NULL REFERENCES schedule_periods(id),
  week_start    DATE    NOT NULL,
  iso_year      INTEGER NOT NULL,
  iso_week      INTEGER NOT NULL,
  workdays_json TEXT    NOT NULL,
  dawn_member_id  INTEGER REFERENCES members(id),
  night_member_id INTEGER REFERENCES members(id),
  version       INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CHECK (dawn_member_id IS NULL OR night_member_id IS NULL
         OR dawn_member_id <> night_member_id),
  UNIQUE (period_id, week_start)
);
CREATE UNIQUE INDEX idx_holiday_date ON holidays(date);
```

---

## 3.5 공정 배정 엔진 설계 (FR-04 / FR-05 / FR-05b 핵심)

> 순수 모듈 `scheduling/engine.py`. DB/HTTP 비의존. 입력→출력만으로 테스트 가능.

### 입력 / 출력
```
입력:  members (active N명), weeks (당직 평일≥1인 주), weights (w_total, w_gap)=기본(1.0,1.0)
출력:  list[(week, dawn_member, night_member)]
```

### 우선순위 점수
```
score(m, week_idx) = w_total * (max_total - m.total)     # 적게 한 사람 ↑ (FR-05)
                   + w_gap   * (week_idx - m.last_idx)    # 오래 쉰 사람 ↑ (FR-05b)
# m.last_idx 미배정자는 -∞ → 최우선
```

### 배정 절차 (주차 순서대로)
```
for week_idx, week in enumerate(weeks):
    cand = sort(members, by score desc, tiebreak=(total asc, last_idx asc, sort_order))
    dawn, night = cand[0], cand[1]    # 서로 다른 사람 보장(FR-04)
    # 각자 덜 한 슬롯 우선 부여(2차: dawn_count vs night_count 균형)
    assign(week, dawn, night)
    for m in (dawn, night): m.total += 1; m.last_idx = week_idx
```

### 보장 속성 (테스트로 검증)
- 총량 균등(FR-05): 종료 시 total 편차 ≤ 1 (N≥2, 주차 충분 시)
- 간격 균일(FR-05b): last_idx 최오래 멤버 우선 → 간격 분산 최소
- 서로 다른 사람(FR-04): night는 dawn 제외 후보
- 결정성: deterministic 타이브레이크 → 같은 입력 = 같은 결과(재현성)
- 엣지: 평일 0인 주 제외, 멤버<2 생성 거부

> **수동 편집의 형평성**: 드래그 교환은 두 셀의 member를 맞바꿔 총 횟수 보존(공정성 유지). 우클릭 수정/삭제는 총량을 바꿀 수 있어, 통계 화면에서 편차를 항상 표시해 사용자가 인지하도록 한다.

---

## 4. API Specification (인증 가드 없음)

### 4.1 Endpoint List

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/members | 명단 조회 |
| POST | /api/members/upload | 엑셀 업로드·명단 추출 |
| PUT | /api/members/{id} | 이름/활성 수정 |
| DELETE | /api/members/{id} | 멤버 삭제 |
| GET | /api/holidays?year= | 공휴일 조회 |
| POST | /api/holidays | 공휴일 추가 |
| PUT | /api/holidays/{id} | 공휴일 수정 |
| DELETE | /api/holidays/{id} | 공휴일 삭제 |
| POST | /api/schedule/generate | 1년 스케줄 생성 |
| GET | /api/schedule?from=&to= | 기간별 배정 조회(캘린더) |
| GET | /api/schedule/stats | 인원별 횟수·간격 통계 |
| GET | /api/schedule/export?format=xlsx | 엑셀 내보내기 |
| **PATCH** | **/api/schedule/week/{id}** | **셀 수정/삭제(우클릭): {slot, member_id\|null, version}** |
| **POST** | **/api/schedule/swap** | **드래그앤드롭 교환: {a_week_id, a_slot, b_week_id, b_slot, a_version, b_version}** |

### 4.2 Detailed Specification (핵심)

#### `POST /api/schedule/generate`
```json
// Request — end_date 미지정 시 시작일+1년. reset=false면 기존 이력 시드(이어 생성)
{ "start_date": "2026-06-01", "end_date": "2026-06-30",
  "weight_total": 1.0, "weight_gap": 1.0, "reset": false }
// Response 201 — 구간 밖 기존 이력을 반영(carried_history_weeks), 누적 형평성 보고
{ "data": { "period_id": 3, "generated_weeks": 5, "generated_workdays": 21,
    "carried_history_weeks": 5, "range": {"start":"2026-06-01","end":"2026-06-30"},
    "fairness": { "total": {"min":2,"max":2,"diff":0}, "gap": {"mean_weeks":5.0,"stdev":0.0} } } }
// 400 { "error": { "code":"VALIDATION_ERROR", "message":"활성 멤버가 2명 이상 필요합니다" } }
```
> **이력 시드(FR-03b)**: 구간을 나눠 생성해도(5월→6월) 구간 밖 기존 주차의 누적 횟수·마지막 근무 주차키를
> 엔진 `initial`로 전달해 누적 형평성을 잇는다. 구간과 겹치는 기존 주차는 교체. `reset=true`면 전체 초기화.

#### `POST /api/schedule/swap`  (드래그앤드롭)
```json
// Request
{ "a_week_id": 12, "a_slot": "dawn", "b_week_id": 18, "b_slot": "night",
  "a_version": 0, "b_version": 2 }
// Response 200 { "data": { "swapped": true } }     // 두 셀 member_id 교환, version++ 
// 409 { "error": { "code":"VERSION_CONFLICT", "message":"스케줄이 변경됨, 새로고침" } }
```

#### `PATCH /api/schedule/week/{id}`  (우클릭 수정/삭제)
```json
// 수정: { "slot": "dawn", "member_id": 7, "version": 0 }
// 삭제: { "slot": "dawn", "member_id": null, "version": 0 }   // 공석
// Response 200 { "data": { "id": 12, "version": 1 } }
// 400 같은 주 새벽=야간 위반 / 409 VERSION_CONFLICT
```

**Error Responses (공통)**: `400` 검증/제약위반 · `404` 없음 · `409` 동시편집 충돌(version) · `500` 서버.

---

## 5. UI/UX Design

### 5.1 Screen Layout

```
┌──────────────────────────────────────────────────────────┐
│  NEXTRADE IT전략본부 당직표                                  │  ← 고정 헤더(로그인 없음)
├──────────────────────────────────────────────────────────┤
│  [캘린더] [통계] [관리(명단·공휴일·생성)]                     │  ← 탭(누구나 접근)
├──────────────────────────────────────────────────────────┤
│   ◀ 2026년 7월 ▶                                          │
│   ┌────┬────┬────┬────┬────┬────┬────┐                    │
│   │ 일 │ 월 │ 화 │ 수 │ 목 │ 금 │ 토 │                    │
│   │    │ 🌅김민수(draggable) 🌙이서연(draggable)  ...      │
│   └────┴────┴────┴────┴────┴────┴────┘                    │
│   · 셀을 끌어다 다른 셀에 놓으면 교환(스위치)                  │
│   · 셀 우클릭 → [수정] [삭제] 컨텍스트 메뉴                   │
└──────────────────────────────────────────────────────────┘
```

### 5.2 User Flow

```
[조회]  URL 접속 → 캘린더 즉시 표시(로그인 없음)
[교환]  새벽/야간 이름 셀 드래그 → 대상 셀에 드롭 → 즉시 스위치
[수정]  셀 우클릭 → 수정 → 담당자 선택 → 반영
[삭제]  셀 우클릭 → 삭제 → 공석 처리
[생성]  관리 탭 → 엑셀 업로드 → 공휴일 확인 → 시작일 입력 → 생성
```

### 5.3 Component List

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `app-header.js` | static/js | 고정 제목·탭 |
| `calendar-view.js` | static/js | 월간 캘린더 렌더(새벽/야간/공휴일), 드래그 핸들 |
| `dnd.js` | static/js | HTML5 드래그앤드롭 — 셀↔셀 교환(POST /swap) |
| `context-menu.js` | static/js | 우클릭 메뉴(수정/삭제 → PATCH) |
| `stats-view.js` | static/js | 인원별 횟수·간격 통계 표 |
| `admin-view.js` | static/js | 엑셀 업로드·공휴일 CRUD·생성 |
| `api.js` | static/js | fetch 래퍼(공통 에러·version 처리) |

### 5.4 Page UI Checklist (v2.1.0)

#### 캘린더 (메인)
- [ ] Header: 고정 제목 'NEXTRADE IT전략본부 당직표' (로그인/사용자 표시 없음)
- [ ] Nav: 이전/다음 달, 오늘 버튼
- [ ] Grid: 월간 7열 캘린더(일~토)
- [ ] Cell: 평일에 🌅새벽 담당자명 / 🌙야간 담당자명 표시
- [ ] Cell: 공휴일/주말 회색 + 공휴일명
- [ ] **Drag**: 새벽/야간 이름 셀이 draggable, 다른 셀에 drop 시 교환
- [ ] **Right-click**: 셀 우클릭 → 컨텍스트 메뉴 [수정][삭제]
- [ ] Edit dialog: 수정 시 담당자 드롭다운(활성 멤버)
- [ ] Delete: 삭제 시 해당 슬롯 공석 표시
- [ ] Conflict: version 충돌 시 "새로고침" 안내

#### 통계
- [ ] Table: 인원별 새벽/야간/합계 횟수
- [ ] Stat: 총량 편차(min/max/diff)
- [ ] Stat: 평균 간격(주)/표준편차

#### 관리 (누구나)
- [ ] Input(file): .xlsx 업로드 + 결과(추가 N/갱신 M)
- [ ] List: 멤버 + 활성 토글 + 이름 수정 + 삭제
- [ ] Holiday: 연도별 목록 + 추가(날짜·이름·유형) + 수정/삭제
- [ ] Generate: 시작일 + 가중치(w_total/w_gap) + [생성] + 결과 요약(공정성)

---

## 6. Error Handling

| Code | HTTP | Cause | Handling |
|------|------|-------|----------|
| VALIDATION_ERROR | 400 | 입력/엑셀 형식·제약(새벽=야간) | 필드별 에러 표시 |
| VERSION_CONFLICT | 409 | 동시 편집으로 version 불일치 | 새로고침 유도 |
| NOT_FOUND | 404 | 리소스 없음 | 안내 |
| SERVER_ERROR | 500 | 서버 오류 | 로그+안내 |

```json
{ "error": { "code": "VERSION_CONFLICT", "message": "스케줄이 변경됨, 새로고침", "details": {} } }
```

---

## 7. Security Considerations

> **조회·일상 편집은 무인증(폐쇄망 내부망이 경계)**, **관리 기능만 경량 2중 게이트**.

### 7.1 관리 기능 게이트 (FR-08b)
- **보호 대상**: `POST /api/members/upload`, `PUT/DELETE /api/members/{id}`, `POST/PUT/DELETE /api/holidays`, `POST /api/schedule/generate`.
- **공개 유지**: 모든 GET, `POST /api/schedule/swap`, `PATCH /api/schedule/week/{id}`(드래그·우클릭 일상 편집).
- **2중 게이트**: (1) **IP 허용목록**(`ADMIN_IPS`, 비우면 비활성) + (2) **공유 비밀번호**(`ADMIN_PASSWORD` 또는 `ADMIN_PASSWORD_HASH`).
- **세션**: 로그인 성공 시 `hmac(SHA256)` 서명 쿠키(`admin_session`, HttpOnly, SameSite=Lax, TTL `ADMIN_TTL`). 추가 의존성 0(표준 라이브러리).
- **엔드포인트**: `POST /api/admin/login`(401 비번오류/403 IP거부), `POST /api/admin/logout`, `GET /api/admin/status`(프론트 게이트 표시용).
- **개인 계정/AD 없음** — 슬림 유지.

### 7.2 일반
- [ ] **외부 호출 0건**: 모든 정적 자산 로컬 번들(CDN/폰트/스크립트 금지).
- [ ] **입력 검증**: Pydantic 스키마. SQL Injection은 SQLAlchemy ORM으로 방지.
- [ ] **엑셀 업로드 안전**: 확장자/용량/시트 검증, 이름 sanitize.
- [ ] **동시성**: version 낙관적 락으로 편집 충돌 방지.
- [ ] **배포 경계**: 사내 폐쇄망에만 게시, 외부망/인터넷 노출 금지(운영 수칙).
- [ ] **민감정보 없음**: 개인정보는 이름만 — 최소 수집. 자격증명·비밀키 미사용.
- [ ] (선택) 변경 로그로 편집 추적성 확보 — 사고 시 원복 참고.

---

## 8. Test Plan (v2.3.0)

### 8.1 Test Scope

| Type | Target | Tool | Phase |
|------|--------|------|-------|
| **L0: Unit** | **배정 엔진·평일/공휴일 계산(핵심)** | pytest | Do |
| L1: API Tests | 엔드포인트 상태·응답·제약 | pytest + httpx TestClient | Do |
| L2: UI Action | 드래그/우클릭/생성 동작 | Playwright | Do |
| L3: E2E | 업로드→생성→편집 여정 | Playwright | Do |

### 8.2 L0: Unit (배정 엔진 — 최우선)

| # | 대상 | 테스트 | 기대 |
|---|------|--------|------|
| 1 | `engine.assign` | N명·52주 | total 편차 ≤ 1 |
| 2 | `engine.assign` | 간격 통계 | 간격 표준편차 ≤ 기준치 |
| 3 | `engine.assign` | 새벽≠야간 | 모든 주 두 멤버 다름 |
| 4 | `engine.assign` | 결정성 | 같은 입력 2회 동일 결과 |
| 5 | `engine.assign` | 멤버 1명 | 검증 에러 |
| 6 | `calendar.workdays` | 공휴일 제외 | 주말·공휴일 미포함, 공휴일 주 4일 |
| 7 | `calendar.weeks` | 부분 주 | 첫 주 부분 평일도 1배정 |

### 8.3 L1: API

| # | Endpoint | Method | 설명 | 상태 | 응답 |
|---|----------|--------|------|:---:|------|
| 1 | /api/schedule/generate | POST | 멤버<2 거부 | 400 | VALIDATION_ERROR |
| 2 | /api/schedule/generate | POST | 정상 생성 | 201 | `.fairness.total.diff` ≤ 1 |
| 3 | /api/schedule | GET | 기간 조회 | 200 | 주차 배열 |
| 4 | /api/schedule/swap | POST | 두 셀 교환 | 200 | member 교환됨 |
| 5 | /api/schedule/swap | POST | version 불일치 | 409 | VERSION_CONFLICT |
| 6 | /api/schedule/week/{id} | PATCH | 새벽=야간 위반 | 400 | VALIDATION_ERROR |
| 7 | /api/schedule/week/{id} | PATCH | 삭제(공석) | 200 | member_id null |
| 8 | /api/members/upload | POST | 엑셀 추출 | 200 | 멤버 N |

### 8.4 L2: UI Action

| # | Page | Action | 기대 |
|---|------|--------|------|
| 1 | 캘린더 | 셀 A를 셀 B로 드래그 | 두 담당자 교환 표시 |
| 2 | 캘린더 | 셀 우클릭 → 수정 → 선택 | 담당자 변경 |
| 3 | 캘린더 | 셀 우클릭 → 삭제 | 공석 표시 |
| 4 | 관리 | 엑셀 업로드 후 생성 | 캘린더 1년 반영 |

### 8.5 L3: E2E

| # | Scenario | Steps | Success |
|---|----------|-------|---------|
| 1 | 생성→조회 | 업로드 → 생성 → 캘린더 | 1년치 표시 |
| 2 | 드래그 교환 | 두 셀 드래그 교환 → 새로고침 | 영속 반영 |
| 3 | 우클릭 편집 | 수정/삭제 → 통계 갱신 | 횟수 반영 |

### 8.6 Seed Data

| Entity | Min | Key Fields |
|--------|:--:|------------|
| members | 6 | name, active=true |
| holidays | 2 | date, name |

---

## 9. Clean Architecture (Python 기능 모듈)

| Layer | Responsibility | Location |
|-------|---------------|----------|
| Presentation | FastAPI 라우터, 정적 JS/CSS, 템플릿 | `*/router.py`, `static/`, `templates/` |
| Application | 유스케이스·오케스트레이션 | `*/service.py` |
| Domain | 순수 규칙 | `scheduling/engine.py`, `scheduling/calendar.py`, `*/schemas.py` |
| Infrastructure | DB·Excel | `db/`, `members/excel.py` |

> Domain(engine)은 외부 계층 import 금지(순수). 인증 계층 없음.

---

## 10. Coding Convention

| Target | Rule | Example |
|--------|------|---------|
| 모듈/파일 | snake_case.py | `schedule_service.py` |
| 함수/변수 | snake_case | `assign_weeks()` |
| 클래스 | PascalCase | `ScheduleWeek` |
| URL | 소문자 | `/api/schedule/swap` |
| JS 파일 | kebab-case.js | `context-menu.js` |

**Env**: `DB_PATH`, `HOST`, `PORT` (인증 관련 없음).
**의존성**: 이 PC pip 21.2.4 → `--break-system-packages` 미지원, `--user` 사용. 외부 자산 로컬 번들.

---

## 11. Implementation Guide

### 11.1 File Structure

```
app/
├── main.py                  # FastAPI 엔트리·정적 마운트·예외핸들러
├── core/config.py           # 환경변수(pydantic-settings)
├── db/{base,session,models}.py
├── members/   {router,service,excel,schemas}.py
├── scheduling/{router,service,engine,calendar,schemas}.py
├── holidays/  {router,service,schemas}.py
├── static/    js/{api,app-header,calendar-view,dnd,context-menu,stats-view,admin-view}.js  css/style.css
└── templates/ index.html   (고정 제목, 단일 페이지)
data/   duty.sqlite
tests/  test_engine.py test_calendar.py test_api_*.py conftest.py
requirements.txt  README.md  run.sh
```

### 11.2 Implementation Order

1. [ ] 기반(core/config, db/models, session, main)
2. [ ] 명단/공휴일(엑셀 추출, 공휴일 CRUD)
3. [ ] **배정 엔진(engine, calendar) + 단위 테스트** ← 최우선
4. [ ] 생성·조회·통계 API
5. [ ] UI(캘린더 + 드래그앤드롭 + 우클릭 + 통계 + 관리)
6. [ ] 폐쇄망 정적 번들·배포 가이드

### 11.3 Session Guide

#### Module Map

| Module | Scope Key | Description | Est. Turns |
|--------|-----------|-------------|:---:|
| 기반 | `module-1` | core/config·db·models·main, 정적 골격 | 25-35 |
| 명단+공휴일 | `module-2` | 엑셀 업로드·멤버 관리, 공휴일 CRUD | 30-40 |
| 배정 엔진 | `module-3` | engine·calendar 순수 모듈 + 단위 테스트 + 생성 API | 40-50 |
| 편집 UI | `module-4` | 캘린더·드래그앤드롭·우클릭·통계·관리 화면 + 정적 번들 | 50-60 |
| 배포 | `module-5` | 폐쇄망 정적 검증·README·실행 스크립트 | 20-30 |

#### Recommended Session Plan

| Session | Phase | Scope |
|---------|-------|-------|
| S1 | Plan + Design | 완료 |
| S2 | Do | `module-1,module-2` |
| S3 | Do | `module-3` (엔진·테스트) |
| S4 | Do | `module-4` (편집 UI) |
| S5 | Do + Check | `module-5` + 전체 검증 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-06-26 | 초안 — Option C 채택 | mirakas |
| 0.2 | 2026-06-26 | 실제 AD 정보·공휴일 수동 반영 | mirakas |
| **0.3** | 2026-06-26 | **대폭 슬림화: 인증/AD·권한·교환승인 제거 → 인증 없는 자유 편집, 드래그앤드롭 교환 + 우클릭 수정/삭제, users·swap_requests 테이블 제거** | mirakas |
| 0.4 | 2026-06-26 | 월간 달력 뷰 확정 + 생성 API 시작/종료일·reset 파라미터 + 엔진 이력 시드(initial)로 증분 형평성(FR-03b) | mirakas |
| 0.5 | 2026-06-26 | 관리 기능 경량 게이트(§7.1): 공유 비밀번호 + IP 허용목록, hmac 서명 쿠키(추가 의존성 0), admin 모듈 추가 | mirakas |
