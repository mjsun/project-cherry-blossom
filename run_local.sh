#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

VENV_PYTHON=".capstone_venv/bin/python"
BACKEND_PORT=8000
FRONTEND_PORT=5173

if [ ! -x "$VENV_PYTHON" ]; then
  echo "venv not found at $VENV_PYTHON" >&2
  exit 1
fi

cleanup() {
  echo "Stopping services..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:$BACKEND_PORT ..."
set -a
source backend/.env
set +a
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}" \
  "$VENV_PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:$FRONTEND_PORT ..."
(cd frontend && npm run dev -- --port "$FRONTEND_PORT") &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
