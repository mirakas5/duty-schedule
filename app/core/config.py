"""환경 설정 — 외부 의존성 없이 .env를 직접 파싱(슬림).

Design Ref: §10 — DB_PATH/HOST/PORT (인증 관련 없음)
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """간단한 .env 파서. 이미 설정된 os.environ 값은 덮어쓰지 않는다.

    인라인 주석(공백+#) 제거. 단 따옴표로 감싼 값이나 '#'이 공백 없이 붙은 경우
    (예: 비밀번호 abc#123)는 보존한다.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if val and val[0] in "\"'":
            # 따옴표 값: 닫는 따옴표까지만
            quote = val[0]
            end = val.find(quote, 1)
            val = val[1:end] if end > 0 else val[1:]
        elif val.startswith("#"):
            # 값 없이 주석만 있는 경우 → 빈 값
            val = ""
        else:
            # 공백+# 이후를 인라인 주석으로 간주해 제거
            val = re.split(r"\s+#", val, maxsplit=1)[0].strip()
        os.environ.setdefault(key, val)


_load_dotenv(ROOT / ".env")


def _csv(value: str):
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings:
    DB_PATH: str = os.environ.get("DB_PATH", "./data/duty.sqlite")
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8080"))

    # ── 관리 기능 게이트 (비밀번호 + IP) ──
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "nextrade")  # ⚠️ 운영 전 변경
    ADMIN_PASSWORD_HASH: str = os.environ.get("ADMIN_PASSWORD_HASH", "")  # 설정 시 우선(sha256 hex)
    ADMIN_IPS = _csv(os.environ.get("ADMIN_IPS", ""))  # 비우면 IP 게이트 비활성(비번만)
    ADMIN_SECRET: str = os.environ.get("ADMIN_SECRET", "change-me-admin-secret")  # 쿠키 서명
    ADMIN_TTL: int = int(os.environ.get("ADMIN_TTL", str(8 * 3600)))  # 관리 세션 유효(초)

    @property
    def db_url(self) -> str:
        db_path = Path(self.DB_PATH)
        if not db_path.is_absolute():
            db_path = ROOT / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"


settings = Settings()
