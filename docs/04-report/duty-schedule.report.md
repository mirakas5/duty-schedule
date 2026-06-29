---
template: report
version: 1.1
feature: duty-schedule
date: 2026-06-29
author: mirakas (IT전략본부)
project: NEXTRADE IT전략본부 당직표
---

# duty-schedule (NEXTRADE IT전략본부 당직표) Completion Report

> **Status**: Complete (테스트 기반 검증, 정식 Check 분석은 생략)
>
> **Project**: NEXTRADE IT전략본부 당직표
> **Author**: mirakas (IT전략본부)
> **Completion Date**: 2026-06-29
> **PDCA Cycle**: #1

---

## Executive Summary

### 1.1 Project Overview

| Item | Content |
|------|---------|
| Feature | duty-schedule (당직표) |
| Start Date | 2026-06-26 |
| End Date | 2026-06-29 |
| Duration | 약 4일 |
| 결과물 | Python 30파일·1,707줄 / 프론트 799줄 / 테스트 31개 / 문서 9 / 배포 스크립트 |

### 1.2 Results Summary

```
┌─────────────────────────────────────────────┐
│  기능 요구사항 완료율: 100% (High 전부)        │
├─────────────────────────────────────────────┤
│  ✅ 완료:     14 / 14 FR (FR-01~FR-12, 05b/06b)│
│  ⏳ 진행중:    0                              │
│  ❌ 취소:      0 (AD인증 등은 요구 변경으로 제외)│
│  🧪 테스트:    31 / 31 통과                    │
└─────────────────────────────────────────────┘
```

### 1.3 Value Delivered

| Perspective | Content |
|-------------|---------|
| **Problem** | 새벽·야간 당직 편성의 수기 작업 시간과 인원 간 형평성 문제 |
| **Solution** | 엑셀 업로드 → 평일 캘린더 기반 자동 배정(총량+간격 공정) + 무인증 웹에서 드래그/클릭 편집. FastAPI+SQLite 단일 서비스. |
| **Function/UX Effect** | 1년치(약 250 평일) 생성 < 2초, **인원별 배정 편차 0~1주 / 간격 표준편차 0.0~0.5**, 달력에서 하루 단위 교환·수정. 외부 네트워크 호출 0건(폐쇄망). |
| **Core Value** | 공정성(균등+간격) + 단순성(로그인·승인 절차 없음) + 자동화 + 폐쇄망 보안 준수 |

---

## 1.4 Success Criteria Final Status

> Plan 문서 기준 최종 평가.

| # | Criteria | Status | Evidence |
|---|---------|:------:|----------|
| SC-1 | 시작~종료일(기본 1년) 평일 당직 자동 생성 | ✅ Met | `engine.assign` + `calendar.build_weeks`, 실측 53주/258일 생성 |
| SC-2 | 인원별 배정 횟수 편차 ≤ 1 | ✅ Met | `test_engine.py` diff≤1 (여러 인원·주차), 실측 diff 0~1 |
| SC-3 | 연속 당직 간격(휴식 주기) 균일 | ✅ Met | 간격 표준편차 0.0~0.5 (실측), `test_gap_uniformity` |
| SC-4 | 같은 주/날 새벽≠야간 | ✅ Met | DB CHECK 제약 + `test_dawn_and_night_are_different` |
| SC-5 | 드래그(하루 단위 교환)·클릭 수정/삭제 동작 | ✅ Met | 스모크 테스트(7/07만 교체 확인), `test_api.py` |
| SC-6 | 외부 네트워크 호출 0건(폐쇄망) | ✅ Met | 정적 자산 전수 로컬, 외부 URL 0건 확인 |
| SC-7 | 핵심 로직 테스트 + 빌드/실행 성공 | ✅ Met | pytest 31개 통과 |
| SC-8 | 민감정보 하드코딩 0건 | ✅ Met | AD 자격·관리 비번 `.env` 분리, 실명·DB git 제외 |

**Success Rate**: 8/8 (100%)

## 1.5 Decision Record Summary

> Plan→Design 핵심 결정과 결과.

| Source | Decision | Followed? | Outcome |
|--------|----------|:---------:|---------|
| [Plan] | 아키텍처 **Option C(실용 균형)** — 기능 모듈 + 엔진 격리 | ✅ | 배정 엔진을 순수 모듈로 분리 → 단위 테스트로 공정성 검증 가능 |
| [Plan] | **슬림화**: AD/LDAP 로그인·권한·승인교환 제거 | ✅ | 무인증 자유 편집 + 관리만 경량 게이트로 단순화 |
| [Design] | **일(日) 단위 저장**으로 전환 (생성은 주 단위) | ✅ | 드래그/수정이 하루만 바뀜(FR-09/10), 주 단위 고정 표시는 유지 |
| [Design] | **Vanilla JS**(외부 의존성 0) + 로컬 번들 | ✅ | 폐쇄망 호환, CDN 0건 |
| [Design] | 관리 게이트 = 공유 비번 + IP (표준 hmac) | ✅ | AD 없이 관리 기능만 보호, 추가 의존성 0 |

---

## 2. Related Documents

| Phase | Document | Status |
|-------|----------|--------|
| Plan | [duty-schedule.plan.md](../01-plan/features/duty-schedule.plan.md) | ✅ Finalized (v0.8) |
| Design | [duty-schedule.design.md](../02-design/features/duty-schedule.design.md) | ✅ Finalized (v0.5) |
| (참고) | [fairness-logic.md](../fairness-logic.md) | ✅ 공정성 알고리즘 설명 |
| Check | docs/03-analysis/duty-schedule.analysis.md | ⚠️ 미작성 (사용자 요청으로 생략, 테스트 31개로 검증 대체) |
| Report | 현재 문서 | ✅ |

---

## 3. Completed Items

### 3.1 Functional Requirements

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| FR-01 | 엑셀 업로드 시 명단 **전체 교체**(+스케줄 초기화) | ✅ | upsert → replace로 변경 |
| FR-02 | 새벽근무(06:30~15:30)·야간근무(13:00~21:30) 슬롯 | ✅ | 시간은 표시 라벨 |
| FR-03 | 시작~종료일 평일 산출·주 그룹화 | ✅ | |
| FR-03b | 증분 생성 시 과거 이력 시드(누적 형평성) | ✅ | 5월→6월 별도 생성 검증 |
| FR-04 | 주 단위 새벽1·야간1(서로 다른 사람) | ✅ | |
| FR-05 | 총량 공정성(편차 ≤1) | ✅ | DOM 스케일로 보장 |
| FR-05b | 간격 공정성(휴식 주기 균일) | ✅ | |
| FR-06 / FR-06b | 수동 공휴일 제외 / 공휴일 낀 주 4일 근무 | ✅ | |
| FR-07 | 공휴일 추가·수정·삭제 | ✅ | |
| FR-08 / FR-08b | 무인증 조회·편집 / 관리 게이트(비번+IP) | ✅ | |
| FR-09 | **드래그앤드롭 하루 단위 교환** | ✅ | 주→일 단위 전환 |
| FR-10 | 클릭/우클릭 수정·삭제(하루) | ✅ | 우클릭 막힘 대비 클릭 지원 |
| FR-11 | 월간 달력 조회 | ✅ | 반응형(대형 모니터 확대) |
| FR-12 | 인원별 통계(근무 주수·일수) | ✅ | |
| FR-13 | 엑셀 내보내기 | ✅ | 일 단위 |

### 3.2 Non-Functional Requirements

| Item | Target | Achieved | Status |
|------|--------|----------|--------|
| 폐쇄망 외부 호출 | 0건 | 0건 | ✅ |
| 1년 생성 성능 | < 2초 | < 1초(로컬) | ✅ |
| 공정성(총량) | 편차 ≤ 1 | 0~1 | ✅ |
| 공정성(간격) | 분산 최소 | σ 0.0~0.5 | ✅ |
| 민감정보 분리 | 하드코딩 0 | 0 (.env/gitignore) | ✅ |
| 반응형 | 대형 모니터 가독 | 1600/2400px 브레이크포인트 | ✅ |

### 3.3 Deliverables

| Deliverable | Location | Status |
|-------------|----------|--------|
| 백엔드 코드 | `app/` (30파일, 1,707줄) | ✅ |
| 프론트엔드 | `app/static/`, `app/templates/` (799줄) | ✅ |
| 배정 엔진(순수) | `app/scheduling/engine.py`, `calendar.py` | ✅ |
| 테스트 | `tests/` (31개) | ✅ |
| 문서 | `docs/` (plan, design, fairness-logic, report) | ✅ |
| 배포 | `deploy/windows/`, `deploy/linux/`, `render.yaml`, `.devcontainer/` | ✅ |
| 형상관리 | GitHub: github.com/mirakas5/duty-schedule (커밋 11) | ✅ |

---

## 4. Incomplete Items

### 4.1 Carried Over to Next Cycle

| Item | Reason | Priority | Estimated Effort |
|------|--------|----------|------------------|
| 정식 Check(analysis) 문서 | 사용자 요청으로 생략(테스트로 대체) | Low | 0.5일 |
| 실서버 운영 배포 | 테스트 단계 | High | 0.5~1일 |
| 변경 이력(감사 로그) | 무인증 편집 추적용(선택) | Medium | 1일 |
| 사내 메일 알림 | 1차 범위 외 | Low | — |

### 4.2 Cancelled/On Hold Items

| Item | Reason | Alternative |
|------|--------|-------------|
| AD/LDAP 로그인 | "슬림하게" 요구로 제외 | 무인증 + 관리 게이트(비번+IP) |
| 사용자 권한 구분(관리자/일반) | 동상 | 누구나 편집, 관리 기능만 게이트 |
| 교환 요청→승인 워크플로우 | 동상 | 드래그앤드롭 즉시 교환 |

---

## 5. Quality Metrics

### 5.1 Final Results

| Metric | Target | Final | 비고 |
|--------|--------|-------|------|
| Design Match Rate | 90% | (정식 Check 미실시) | 테스트 31개 통과로 기능 검증 |
| Test | 통과 | **31/31 통과** | engine 17 + calendar 9 + api 5 (회귀 포함) |
| 외부 의존성(프론트) | 0 | 0 | CDN/폰트/스크립트 전부 로컬 |
| 보안 이슈 | 0 Critical | 0 | 비번·자격 .env 분리, 실명 git 제외 |

### 5.2 Resolved Issues (개발 중 해결)

| Issue | Resolution | Result |
|-------|------------|--------|
| AD 비밀번호 평문 노출 | `.env` 분리 + AD 기능 자체 제거 | ✅ |
| Python 3.9 `Mapped[int\|None]` 오류 | `Optional[int]`로 변경 | ✅ |
| `.env` 인라인 주석이 값에 혼입 → 로그인 500 | 파서 주석 제거 + bytes 비교 | ✅ |
| Windows `.bat` 실행 불가(LF) | CRLF + chcp 65001 + py 런처 인식 | ✅ |
| requirements cp949 디코딩 오류 | ASCII화 | ✅ |
| Windows SQLite 경로 | `as_posix()` | ✅ |
| 48" 모니터 작게 표시 | 반응형(폭·글자 확대) | ✅ |

---

## 6. Lessons Learned & Retrospective

### 6.1 What Went Well (Keep)
- 배정 엔진을 **순수 모듈로 격리** → 공정성을 단위 테스트로 확실히 검증.
- 요구 변경(슬림화·일 단위·관리 게이트)에 모듈 구조 덕분에 **국소 수정**으로 대응.
- 발생한 실수를 [lessons.md](../../lessons.md)에 즉시 규칙화 → 재발 방지.

### 6.2 What Needs Improvement (Problem)
- 요구사항이 여러 번 크게 바뀜(AD→무인증, 주→일) → 초기 요구 확정이 더 단단했으면 재작업 감소.
- 정식 Check(분석) 단계를 건너뜀 → 설계-구현 일치율 수치화 자료 부재.
- 배포(특히 폐쇄망 Windows) 환경 차이로 인코딩/줄바꿈 이슈가 뒤늦게 노출.

### 6.3 What to Try Next (Try)
- 배포 대상 환경(인코딩/줄바꿈) 체크리스트를 Do 단계에 포함.
- 변경 잦은 기능은 Plan 단계에서 "확정/가변" 항목 구분.

---

## 7. Next Steps

### 7.1 Immediate
- [ ] 실서버 배포 (Linux systemd 권장 / 폐쇄망 Windows 가이드)
- [ ] `.env`의 `ADMIN_PASSWORD`·`ADMIN_SECRET` 운영값으로 변경
- [ ] 실제 명단으로 1년 스케줄 생성 후 사내 공유

### 7.2 Next PDCA Cycle (선택)
| Item | Priority |
|------|----------|
| 변경 이력(감사 로그) | Medium |
| 정식 Check 분석 문서화 | Low |
| 사내 메일 알림 연동 | Low |

---

## 8. Changelog

### v0.1.0 (2026-06-29)
**Added:**
- 평일 새벽/야간 당직 자동 배정(총량+간격 공정성)
- 월간 달력 조회 + 하루 단위 드래그 교환 + 클릭 수정/삭제
- 엑셀 명단 업로드(전체 교체), 공휴일 수동 관리, 통계, 엑셀 내보내기
- 관리 기능 게이트(공유 비밀번호 + IP)
- 폐쇄망 Windows / Linux 배포 가이드 + 스크립트, Render/Codespaces 설정
- 반응형 UI(대형 모니터 대응)

**Changed:**
- 시간대: 오전/야간 당직 → 새벽근무(06:30~15:30)/야간근무(13:00~21:30)
- 인증: AD/LDAP → 무인증 + 관리 게이트
- 저장: 주 단위 → 일 단위(드래그 하루 교환)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-06-29 | 완료 보고서 작성 | mirakas |
