# Lessons — 재발방지 규칙

> 작업 중 발견된 실수 패턴과 재발방지 룰. (CLAUDE.md 규칙)

## L1. 서버 실행 중 SQLite 파일 삭제 금지
- **증상**: `sqlite3.OperationalError: attempt to write a readonly database`
- **원인**: uvicorn이 `data/duty.sqlite`를 연 상태에서 파일을 `rm` → unlink된 inode에 쓰기 시도 → readonly.
- **룰**: DB 파일 정리·백업은 **반드시 서버 중지 후** 수행. 스모크 테스트 후 정리할 땐 서버부터 stop.

## L2. .env 인라인 주석이 값에 섞임
- **증상**: 비밀번호 비교 시 `TypeError: comparing strings with non-ASCII characters` (한글 주석이 값에 포함), `ADMIN_IPS`에 주석 문자열이 IP로 파싱됨.
- **원인**: 단순 .env 파서가 `KEY=value   # 주석` 의 인라인 주석을 제거하지 않음.
- **룰**: .env 파서는 (1) 따옴표 값 보존, (2) `공백+#` 이후 주석 제거, (3) 값이 `#`로 시작하면 빈 값 처리. 비밀번호에 `#`가 필요하면 따옴표로 감쌀 것.

## L3. Python 3.9에서 SQLAlchemy `Mapped[int | None]` 금지
- **증상**: `Could not resolve all types within mapped annotation: "Mapped[int | None]"`
- **원인**: PEP 604 `X | None` 런타임 평가가 3.9 미지원(`from __future__ import annotations` 있어도 SQLAlchemy가 eval).
- **룰**: 3.9 타깃에선 `Mapped[Optional[int]]` 사용.

## L4. hmac.compare_digest는 ASCII str 한정
- **룰**: 사용자 입력 비밀번호 비교는 `a.encode("utf-8")` 후 bytes로 비교해 non-ASCII 안전 확보.

## L5. 포트 충돌
- **증상**: `[Errno 48] address already in use` (8080을 다른 앱이 점유).
- **룰**: 기동 전 `lsof -nP -iTCP:<port> -sTCP:LISTEN` 확인. 점유 시 다른 포트(`PORT=8090`) 사용, 타 프로세스는 건드리지 않음.
