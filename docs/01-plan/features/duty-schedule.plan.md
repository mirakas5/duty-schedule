---
template: plan
version: 1.3
feature: duty-schedule
date: 2026-06-26
author: mirakas (IT전략본부)
project: NEXTRADE IT전략본부 당직표
version_project: 0.1
status: Draft
---

# duty-schedule (NEXTRADE IT전략본부 당직표) Planning Document

> **Summary**: 명단 엑셀을 업로드하면 평일 캘린더 기반 1년치 새벽/야간 근무를 공정 배정하고, **로그인 없이 누구나** 드래그앤드롭 교환·우클릭 수정/삭제로 자유롭게 편집하는 사내 폐쇄망 웹 앱.
>
> **Project**: NEXTRADE IT전략본부 당직표
> **Version**: 0.1
> **Author**: mirakas (IT전략본부)
> **Date**: 2026-06-26
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 새벽·야간 근무 편성을 수기로 하면 시간이 많이 들고, 인원 간 횟수·간격의 형평성을 맞추기 어렵다. |
| **Solution** | 명단 엑셀 업로드 → 평일 캘린더 기반 1년치 근무를 공정 배정(총량+간격)하고, 인증 없이 누구나 드래그앤드롭·우클릭으로 즉시 편집하는 슬림 웹 앱(FastAPI+SQLite). |
| **Function/UX Effect** | 편성 시간을 수 초로 단축, 직관적 드래그/우클릭 편집으로 별도 교육 없이 사용, 전사 공유로 항상 최신 당직표 유지. |
| **Core Value** | 공정성(균등 분배) + 단순성(로그인·승인 절차 없음) + 자동화(1년 자동 편성) + 폐쇄망 보안 준수. |

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 수기 당직 편성의 시간 소모와 인원 간 형평성 문제 해소 |
| **WHO** | IT전략본부 임직원 누구나(권한 구분·로그인 없음) |
| **RISK** | 폐쇄망 제약(외부 CDN/API 불가) + 공정 분배 형평성 미흡 + 인증 없는 자유 편집의 실수/충돌 |
| **SUCCESS** | 1년 평일 당직 자동 생성, 인원별 배정 횟수 편차 ≤1 + 연속 당직 간격 균일, 드래그/우클릭 편집 동작, 외부호출 0 |
| **SCOPE** | Phase 1: 기반, Phase 2: 명단/공휴일, Phase 3: 배정 엔진, Phase 4: 편집 UI(드래그·우클릭), Phase 5: 배포 |

---

## 1. Overview

### 1.1 Purpose

IT전략본부 임직원의 평일 당직 근무(새벽근무 06:30~15:30 / 야간근무 13:00~21:30)를 1년 단위로 공정하게 자동 편성하고, **로그인 없이 누구나** 웹에서 직관적으로 조회·수정할 수 있도록 한다.

### 1.2 Background

- 현재 당직표는 수기/엑셀로 편성되어 작성 시간이 길고, 특정 인원에게 당직이 몰리는 형평성 문제가 발생한다.
- 보안 정책상 업무 PC는 폐쇄망에 있어 외부 인터넷/CDN/API에 접근할 수 없다.
- **단순함 우선**: 인증·승인 등 복잡한 절차를 배제하고, 내부망 신뢰를 전제로 누구나 자유롭게 편집한다.

### 1.3 Related Documents

- Requirements: 본 문서 (사용자 채팅 요구사항 기반)
- References: Design 문서 `duty-schedule.design.md`

---

## 2. Scope

### 2.1 In Scope

- [ ] 임직원 명단 엑셀(`.xlsx`, 이름 컬럼) 업로드 및 인원 추출
- [ ] 새벽근무(06:30~15:30) / 야간근무(13:00~21:30) 2개 슬롯 (시간은 표시 라벨)
- [ ] **주(週) 단위 고정**: 한 주는 새벽 1명·야간 1명이 그 주 평일 내내 유지
- [ ] **평일만** 배정(주말 제외), 관리자 수동 지정 공휴일 제외(공휴일 낀 주는 4일 근무)
- [ ] 한 주 내 새벽 담당자와 야간 담당자는 **서로 다른 사람**
- [ ] 실제 캘린더 기반 **1년치** 스케줄 자동 생성
- [ ] **공정 분배**: (1) 인원별 새벽·야간 횟수 균등 + (2) 연속 당직 간격(휴식 주기) 균일
- [ ] 공휴일 수동 지정(추가/수정/삭제)
- [ ] **로그인·인증 없음 — 누구나 자유 편집**
- [ ] **드래그앤드롭 교환**: 두 셀을 드래그로 맞바꿔 즉시 스위치
- [ ] **우클릭 컨텍스트 메뉴**: 셀 우클릭 → 수정(담당자 변경) / 삭제(공석 처리)
- [ ] 캘린더/주간 형태 조회 + 인원별 통계(횟수·간격)
- [ ] UI 제목 고정: **'NEXTRADE IT전략본부 당직표'**
- [ ] **폐쇄망 단일 배포**: 모든 의존성(JS/CSS/폰트) 로컬 번들, 외부 호출 0건
- [ ] 데이터는 서버(SQLite) 공유 — 모든 임직원이 같은 최신 당직표 조회

### 2.2 Out of Scope

- ~~AD·LDAP 연동 로그인~~ **(제외 — 슬림화)**. 단, 관리 기능만 **공유 비밀번호+IP** 경량 게이트(FR-08b)
- ~~개인별 계정/세션~~ **(제외)** — 일상 편집은 누구나, 관리만 공유 비밀번호
- ~~교환 요청·승인 워크플로우~~ **(제외 — 드래그앤드롭 즉시 교환으로 대체)**
- 주말·공휴일 당직 (평일만)
- 모바일 네이티브 앱 / 외부 알림 / 급여·근태 연동 / 다국어

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 이름 컬럼이 포함된 `.xlsx`를 업로드하면 **기존 명단을 전체 삭제하고 새 명단으로 교체**한다(명단 변경 시 기존 스케줄도 초기화) | High | Pending |
| FR-02 | 새벽근무·야간근무 2개 슬롯을 정의한다(시간은 표시 라벨, 중복 무관) | High | Pending |
| FR-03 | 지정 **시작일~종료일**(종료일 미지정 시 기본 1년)의 **평일**을 산출하고 주(월~금) 단위로 그룹화한다 | High | Pending |
| FR-03b | **[증분 생성·이력 시드]** 구간을 나눠 생성해도(예: 5월 생성 후 6월 별도 생성) 구간 밖 기존 이력의 누적 횟수·마지막 근무 시점을 시드로 삼아 누적 형평성을 잇는다. 구간과 겹치는 기존 주차는 교체한다 | High | Pending |
| FR-04 | 주 단위로 새벽 1명·야간 1명(서로 다른 사람)을 배정하고 그 주 평일 전체에 적용한다 | High | Pending |
| FR-05 | **[총량 공정성]** 인원별 새벽·야간 누적 횟수 편차가 최소가 되게 배분한다(목표 ≤1) | High | Pending |
| FR-05b | **[간격 공정성]** 각 인원의 마지막 근무 후 다음 근무까지의 간격을 균일하게 유지한다(경과 주차가 큰 인원 우선 배정) | High | Pending |
| FR-06 | 관리자 없이 누구나 **수동 지정**한 공휴일을 당직 평일에서 제외한다(내장 데이터 없음) | High | Pending |
| FR-06b | 공휴일이 낀 주도 주 단위 고정 유지 — 공휴일 제외한 나머지 평일만 근무(예: 공휴일 1일 → 4일) | High | Pending |
| FR-07 | 공휴일을 UI에서 추가·수정·삭제한다 | Medium | Pending |
| FR-08 | 조회·일상 편집(드래그·우클릭)은 **로그인 없이 누구나** 사용한다 | High | Pending |
| FR-08b | **관리 기능(명단 업로드·스케줄 생성·공휴일 편집)** 은 **공유 관리자 비밀번호 + IP 허용목록** 2중 게이트로 보호한다(개인 계정/AD 없음). 비밀번호는 .env 분리, 쿠키는 표준 hmac 서명 | High | Pending |
| FR-09 | **드래그앤드롭**으로 두 셀(**하루·슬롯**)의 담당자를 즉시 맞바꾼다 — 자동 생성은 주 단위지만 교환은 **하루 단위**로만 바뀐다 | High | Pending |
| FR-10 | **셀 클릭(또는 우클릭) 메뉴**로 해당 **하루** 슬롯의 담당자 수정/삭제(공석)를 수행한다 (우클릭이 막히는 환경 대비 클릭 지원) | High | Pending |
| FR-11 | **월간 달력** 형태로 당직표를 조회한다(월 이동, 공휴일/주말 표시, 제목 'NEXTRADE IT전략본부 당직표') | High | Pending |
| FR-12 | 인원별 새벽/야간 횟수·간격 통계를 조회한다 | Medium | Pending |
| FR-13 | 생성된 스케줄을 엑셀/인쇄용으로 내보낸다 | Low | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| 폐쇄망 호환 | 외부 네트워크 호출 0건(CDN/폰트/API 전부 로컬 번들) | 브라우저 Network 탭 외부 도메인 0건 |
| 단순성 | 로그인·설치 없이 URL 접속만으로 즉시 사용 | 사용 흐름 점검 |
| 공정성(총량) | 인원별 새벽·야간 배정 횟수 편차 ≤ 1 | 생성 결과 통계 검증 |
| 공정성(간격) | 인원별 연속 당직 간격(주차)의 분산 최소화 | 간격 표준편차 통계 검증 |
| 성능 | 1년치(약 52주) 생성 < 2초, 드래그/편집 응답 즉시 | 로컬 벤치마크 |
| 데이터 일관성 | 동시 편집 시 충돌 방지(낙관적 락) | 충돌 시 새로고침 안내 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] 모든 High 우선순위 FR 구현
- [ ] 엑셀 업로드 → 1년 평일 스케줄 자동 생성 동작
- [ ] 드래그앤드롭 교환 + 우클릭 수정/삭제 동작
- [ ] 외부 네트워크 호출 0건(폐쇄망 검증) 통과
- [ ] 배정 엔진 단위 테스트 + 통합 테스트 통과
- [ ] 배포 가이드(README) 작성

### 4.2 Quality Criteria

- [ ] 총 횟수 편차 ≤ 1 검증 테스트 통과
- [ ] 인원별 연속 당직 간격 표준편차 기준치 이하 검증 테스트 통과
- [ ] 핵심 로직(배정 엔진, 평일/공휴일 계산) 테스트 커버리지 ≥ 80%
- [ ] 빌드/실행 성공, 외부 의존성 0

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 폐쇄망에서 외부 의존성 로드 실패 | High | High | 모든 JS/CSS/폰트 로컬 번들, 빌드 단계 외부 URL 검사 |
| 공정 분배가 실제로 균등하지 않음 | High | Medium | 가중치 결합 점수(총량+간격) 알고리즘 + 통계 검증 테스트 |
| 인증 없는 자유 편집으로 실수/되돌리기 곤란 | Medium | Medium | 낙관적 락 + 변경 즉시 반영, (선택)변경 로그로 추적, 재생성으로 초기화 |
| 동시 드래그/편집 데이터 충돌 | Medium | Low | SQLite 트랜잭션 + version 컬럼(충돌 시 새로고침 유도) |
| 공휴일 수동 등록 누락 | Medium | Medium | 미등록 시 평일 간주됨을 UI에서 안내 |

---

## 6. Impact Analysis

> 신규 그린필드 프로젝트 — 기존 소비자 없음.

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| `members` | DB Model | 당직 대상 인원 명단(엑셀 추출) 신규 |
| `holidays` | DB Model | 공휴일/지정일(수동) 신규 |
| `schedule_periods` | DB Model | 생성 단위(1년) 신규 |
| `schedule_weeks` | DB Model | 주 단위 새벽·야간 배정 신규 |

### 6.3 Verification

- [x] 신규 프로젝트로 기존 소비자 영향 없음

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Selected |
|-------|:--------:|
| Starter | ☐ |
| **Dynamic** (인증 없는 단일 FastAPI+SQLite 웹앱) | ☑ |
| Enterprise | ☐ |

### 7.2 Key Architectural Decisions

| Decision | Selected | Rationale |
|----------|----------|-----------|
| Backend | **FastAPI** | 비동기·타입 안전, 단일 서비스 |
| Web UI | **FastAPI 내장 정적 서빙 + Vanilla JS** | 폐쇄망 단일 배포 최단 경로 |
| 인증 | **없음** | 슬림화 — 내부망 신뢰 전제, 누구나 편집 |
| Excel 처리 | **openpyxl** | 가벼움, `.xlsx` 직접 처리 |
| DB | **SQLite(파일)** | 설치 불필요, 단일 파일 공유 |
| ORM | **SQLAlchemy** | 트랜잭션·낙관적 락 |
| 교환 | **드래그앤드롭 즉시 스위치** | 승인 절차 제거 |
| 셀 편집 | **우클릭 컨텍스트 메뉴(수정/삭제)** | 직관적 직접 편집 |
| 프론트 | **Vanilla JS(외부 CDN 금지)** | 의존성 최소화 |

### 7.3 Folder Structure Preview

```
app/
  main.py
  core/config.py
  db/{base,session,models}.py
  members/   {router,service,excel,schemas}.py
  scheduling/{router,service,engine,calendar,schemas}.py   # engine=순수 모듈
  holidays/  {router,service,schemas}.py
  static/    js/ css/ (로컬 번들)
  templates/ index.html  (고정 제목, SPA 단일 페이지)
data/  duty.sqlite
tests/ test_engine.py 등
```

---

## 8. Convention Prerequisites

### 8.3 Environment Variables Needed

| Variable | Purpose | To Be Created |
|----------|---------|:-------------:|
| `DB_PATH` | SQLite 파일 경로 | ☑ |
| `HOST` / `PORT` | 서버 바인드(폐쇄망 내부) | ☑ |

> 인증 제거로 AD/세션 관련 환경변수 불필요.

---

## 9. Next Steps

1. [ ] 설계 문서 갱신 완료(`duty-schedule.design.md`) — 인증 제거·드래그/우클릭 반영
2. [ ] 구현 시작(`/pdca do duty-schedule --scope module-N`)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-06-26 | 초안 작성 | mirakas |
| 0.2 | 2026-06-26 | 간격 공정성(FR-05b) 추가 | mirakas |
| 0.3 | 2026-06-26 | 근무 슬롯 명칭·시간대 변경(새벽/야간근무) | mirakas |
| 0.4 | 2026-06-26 | 공휴일 수동 지정, AD 연결정보 반영 | mirakas |
| **0.5** | 2026-06-26 | **대폭 슬림화: 로그인/AD·권한·승인교환 제거 → 인증 없이 누구나 편집, 드래그앤드롭 교환 + 우클릭 수정/삭제** | mirakas |
| 0.6 | 2026-06-26 | 월간 달력 뷰 + 시작/종료일 구간 생성 + 과거 이력 시드 형평성(FR-03/03b) | mirakas |
| 0.7 | 2026-06-26 | 관리 기능 경량 게이트(FR-08b): 공유 비밀번호 + IP 허용목록(AD 없이, 관리 탭만) | mirakas |
| 0.8 | 2026-06-29 | 저장을 일(日) 단위로 전환 — 드래그/수정이 하루만 바뀜(FR-09/10), 우클릭 막힘 대비 클릭 메뉴 추가 | mirakas |
