#!/usr/bin/env bash
set -euo pipefail

# Optional helper: fetch Adafruit CircuitPython Library Bundle and vendor the
# GC9A01A driver into circuitpython/lib/.
#
# This repo vendors `adafruit_gc9a01a.py` already (text, drop-in).
# Use this script if you want to refresh it from upstream.
#
# Usage:
#   ./tools/vendor_adafruit_libs.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_LIB="$ROOT_DIR/circuitpython/lib"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

BUNDLE_URL="https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/latest/download/adafruit-circuitpython-bundle-py.zip"

echo "Downloading bundle..."
curl -L "$BUNDLE_URL" -o "$TMP_DIR/bundle.zip"

echo "Extracting..."
unzip -q "$TMP_DIR/bundle.zip" -d "$TMP_DIR/bundle"

# Copy Python source (not .mpy) for readability and easy diffing.
SRC_FILE="$(find "$TMP_DIR/bundle" -type f -name 'adafruit_gc9a01a.py' | head -n 1)"
if [[ -z "${SRC_FILE:-}" ]]; then
  echo "Could not find adafruit_gc9a01a.py in bundle." >&2
  exit 1
fi

mkdir -p "$OUT_LIB"
cp "$SRC_FILE" "$OUT_LIB/adafruit_gc9a01a.py"

echo "Updated: $OUT_LIB/adafruit_gc9a01a.py"

