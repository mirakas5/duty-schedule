# NEXTRADE IT전략본부 당직표

평일 새벽/야간 당직을 공정하게 자동 편성하고, 브라우저에서 드래그앤드롭·우클릭으로 자유롭게 편집하는 사내 웹 앱.
**로그인 없음** — 폐쇄망 내부에서 누구나 사용.

## 특징

- 이름 엑셀 업로드 → 1년치 평일 당직 자동 생성
- 공정 분배: 인원별 횟수 균등(편차 ≤ 1) + 휴식 간격 균일
- 새벽근무(06:30~15:30) / 야간근무(13:00~21:30), 주 단위 고정, 서로 다른 사람
- 공휴일 수동 지정(낀 주는 4일 근무)
- **드래그앤드롭** 으로 교환, **우클릭** 으로 수정/삭제
- 인원별 통계(횟수·간격), 엑셀 내보내기
- 외부 네트워크 호출 0건(폐쇄망)

## 배포

환경별 단계별 가이드: **[deploy/README.md](deploy/README.md)**
- **폐쇄망 Windows PC** → [deploy/windows/DEPLOY_WINDOWS.md](deploy/windows/DEPLOY_WINDOWS.md) (USB 반입 + `.bat`)
- **Linux 서버** (온라인/폐쇄망) → [deploy/linux/DEPLOY_LINUX.md](deploy/linux/DEPLOY_LINUX.md) (venv + systemd 자동 구동)

## 설치 (개발/Mac·Linux)

```bash
python3 -m pip install --user -r requirements.txt
#   ※ 이 PC의 pip이 구버전(21.x)이면 --break-system-packages 미지원 → --user 사용
```

## 실행

```bash
./run.sh
# 또는
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

브라우저에서 `http://<서버IP>:8080` 접속.

## 사용 순서

1. **관리** 탭 → 이름이 든 `.xlsx` 업로드 (샘플: `data/sample_members.xlsx`)
2. (선택) 공휴일 등록
3. 시작일 지정 후 **자동 생성**
4. **주간 당직표** 탭에서 조회 / 드래그 교환 / 우클릭 수정·삭제

## 데이터

- SQLite 파일: `data/duty.sqlite` (자동 생성, 모든 사용자 공유)
- 백업: 해당 파일 복사

## 구조

```
app/
  main.py                 FastAPI 엔트리
  core/config.py          환경설정(.env)
  db/                     모델·세션 (members/holidays/periods/weeks)
  members/                엑셀 업로드·명단
  scheduling/             engine(공정배정 순수)·calendar·service·router
  holidays/               공휴일 CRUD
  static/, templates/     로컬 번들 UI(외부 CDN 없음)
tests/                    pytest (배정 엔진·캘린더)
```

## 테스트

```bash
python3 -m pytest tests/ -v
```
