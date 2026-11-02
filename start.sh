#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
URL="http://127.0.0.1:8765"

# Keep Fedora awake for as long as this launcher is running.
if [ "${MDZ_INHIBITED:-0}" != "1" ] && command -v systemd-inhibit >/dev/null 2>&1; then
  exec systemd-inhibit \
    --what=idle:sleep \
    --mode=block \
    --why="MDZ SkyScan is running" \
    env MDZ_INHIBITED=1 "$0" "$@"
fi

cd "$ROOT"
python3 app.py &
SERVER_PID=$!
cleanup(){ kill "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Give the local server a moment to start.
for _ in $(seq 1 30); do
  if python3 - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=.25).read()
PY
  then break; fi
  sleep .2
done

if command -v firefox >/dev/null 2>&1; then
  firefox --new-instance --kiosk "$URL"
elif command -v chromium >/dev/null 2>&1; then
  chromium --start-fullscreen --app="$URL"
elif command -v chromium-browser >/dev/null 2>&1; then
  chromium-browser --start-fullscreen --app="$URL"
else
  xdg-open "$URL"
  wait "$SERVER_PID"
fi
