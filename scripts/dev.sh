#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

export PORT="${PORT:-8001}"
export DISPLAY_DRIVER="${DISPLAY_DRIVER:-mock}"
export GIF_DIR="${GIF_DIR:-$ROOT_DIR/_local_gifs}"

mkdir -p "$GIF_DIR"

echo "Starting backend on :$PORT (DISPLAY_DRIVER=$DISPLAY_DRIVER, GIF_DIR=$GIF_DIR)"
(cd "$BACKEND_DIR" && source .venv/bin/activate && python run_server.py) &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting frontend on :5173 (proxy -> http://127.0.0.1:$PORT)"
cd "$FRONTEND_DIR"
VITE_API_TARGET="http://127.0.0.1:$PORT" npm run dev

