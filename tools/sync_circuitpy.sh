#!/usr/bin/env bash
set -euo pipefail

# Sync `circuitpython/` fileset to a mounted CIRCUITPY drive.
#
# Usage:
#   CIRCUITPY=/Volumes/CIRCUITPY ./tools/sync_circuitpy.sh
#   ./tools/sync_circuitpy.sh                # uses /Volumes/CIRCUITPY by default (macOS)

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/circuitpython"
DEST_DIR="${CIRCUITPY:-/Volumes/CIRCUITPY}"

if [[ ! -d "$DEST_DIR" ]]; then
  echo "CIRCUITPY drive not found at: $DEST_DIR" >&2
  echo "Set CIRCUITPY=/path/to/CIRCUITPY and re-run." >&2
  exit 1
fi

echo "Syncing:"
echo "  from: $SRC_DIR/"
echo "    to: $DEST_DIR/"

rsync -av --delete \
  --exclude ".DS_Store" \
  --exclude "__pycache__" \
  "$SRC_DIR/" "$DEST_DIR/"

echo "Done. If code doesn't reload, press the QT Py reset button."

