#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

export PORT="${PORT:-8000}"
export DISPLAY_DRIVER="${DISPLAY_DRIVER:-mock}"
export GIF_DIR="${GIF_DIR:-$ROOT_DIR/_local_gifs}"

mkdir -p "$GIF_DIR"

if [[ -d "$FRONTEND_DIR" ]]; then
  echo "Building UI (frontend/dist)..."
  (cd "$FRONTEND_DIR" && npm install && npm run build)
fi

echo "Starting single-process app on :$PORT (UI + API)"
cd "$BACKEND_DIR"
source .venv/bin/activate
python run_server.py

