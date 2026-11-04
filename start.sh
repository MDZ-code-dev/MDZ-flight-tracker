#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [ ! -x /usr/bin/python3 ]; then
  echo "Python 3 is missing. Install it, then run bash install.sh in this folder." >&2
  exit 1
fi
# The checker prints only a verified interpreter path; do not fall back to a
# random PATH Python that cannot see Fedora's system GI bindings.
MDZ_PYTHON="$(/usr/bin/python3 -I "$ROOT/linux_setup.py" --print-python)"
if command -v systemd-inhibit >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
  exec systemd-inhibit --what=idle:sleep --mode=block \
    --why="MDZ SkyScan is running" "$MDZ_PYTHON" "$ROOT/desktop.py"
fi
exec "$MDZ_PYTHON" "$ROOT/desktop.py"
