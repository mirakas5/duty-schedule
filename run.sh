#!/usr/bin/env bash
# NEXTRADE IT전략본부 당직표 - 실행 스크립트
set -e
cd "$(dirname "$0")"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

echo "[당직표] http://${HOST}:${PORT} 에서 기동합니다..."
python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT"
