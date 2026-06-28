# 배포 가이드 (Deploy)

NEXTRADE IT전략본부 당직표를 서버에 올리는 방법. 환경에 맞는 가이드를 따라가세요.

| 환경 | 가이드 | 요약 |
|------|--------|------|
| **폐쇄망 Windows PC** (테스트) | [windows/DEPLOY_WINDOWS.md](windows/DEPLOY_WINDOWS.md) | 인터넷 PC에서 wheel 받아 USB로 반입 → `.bat`로 설치·실행. 방화벽 개방. |
| **Linux 서버** (온라인/폐쇄망) | [linux/DEPLOY_LINUX.md](linux/DEPLOY_LINUX.md) | venv + pip(또는 오프라인 wheel) → **systemd 서비스**로 상시 구동·자동 재시작. |

## 공통 보안 수칙
- `.env`의 `ADMIN_PASSWORD`·`ADMIN_SECRET`를 **반드시 변경** (기본 `nextrade` 금지)
- 조회·일상 편집은 무인증(설계 의도) → **내부망에서만** 게시, 외부 공개 금지
- 실명 명단 엑셀·`data/duty.sqlite`(개인정보)는 git/외부 반출 금지 (`.gitignore` 처리됨)
- 관리 기능(명단/생성/공휴일)은 공유 비밀번호 + (선택)IP 허용목록으로 보호됨

## 빠른 선택
- 사내에 **리눅스 서버**가 있다 → Linux 가이드 (가장 안정적, 자동 재시작)
- **Windows PC 한 대**로 임시 테스트 → Windows 가이드
- 그냥 **내 PC(Mac/Linux)에서 잠깐** → 루트 [README.md](../README.md)의 실행 명령
