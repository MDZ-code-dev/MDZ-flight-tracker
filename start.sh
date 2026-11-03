#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
URL="http://127.0.0.1:8765"
LOG_DIR="$HOME/.local/state/mdz-skyscan"
LOG_FILE="$LOG_DIR/server.log"

mkdir -p "$LOG_DIR"
cd "$ROOT"

server_ready() {
  python3 - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=.35).read()
PY
}

# Start the local tracker server only if it is not already running.
# The server itself is wrapped in systemd-inhibit so Fedora stays awake
# even if Chromium/Chrome hands the window off to an existing process.
if ! server_ready; then
  if command -v systemd-inhibit >/dev/null 2>&1; then
    nohup systemd-inhibit \
      --what=idle:sleep \
      --mode=block \
      --why="MDZ SkyScan is running" \
      python3 "$ROOT/app.py" >"$LOG_FILE" 2>&1 &
  else
    nohup python3 "$ROOT/app.py" >"$LOG_FILE" 2>&1 &
  fi

  for _ in $(seq 1 40); do
    if server_ready; then
      break
    fi
    sleep .2
  done
fi

if ! server_ready; then
  echo "MDZ SkyScan server failed to start."
  echo "Log: $LOG_FILE"
  exit 1
fi

# Open in a browser. The server stays alive in the background.
if command -v chromium >/dev/null 2>&1; then
  chromium --start-fullscreen --app="$URL" >/dev/null 2>&1 &
elif command -v chromium-browser >/dev/null 2>&1; then
  chromium-browser --start-fullscreen --app="$URL" >/dev/null 2>&1 &
elif command -v google-chrome >/dev/null 2>&1; then
  google-chrome --start-fullscreen --app="$URL" >/dev/null 2>&1 &
elif command -v firefox >/dev/null 2>&1; then
  firefox --kiosk "$URL" >/dev/null 2>&1 &
else
  xdg-open "$URL" >/dev/null 2>&1 &
fi

exit 0
