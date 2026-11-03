#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PYTHON=python3
if [ -x "$ROOT/.venv/bin/python" ]; then
  PYTHON="$ROOT/.venv/bin/python"
fi
if command -v systemd-inhibit >/dev/null 2>&1; then
  exec systemd-inhibit --what=idle:sleep --mode=block \
    --why="MDZ SkyScan is running" "$PYTHON" "$ROOT/desktop.py"
fi
exec "$PYTHON" "$ROOT/desktop.py"
