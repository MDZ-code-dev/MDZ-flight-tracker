#!/usr/bin/env bash
# Test the shipped download's installer, preserving simulated user files.
set -euo pipefail
trap 'echo "::error::Linux download installation failed at line $LINENO" >&2' ERR
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="${RUNNER_TEMP:-/tmp}/mdz-linux-install"
APP_ROOT="$TEST_ROOT/App with spaces/MDZ-SkyScan"
mkdir -p "$TEST_ROOT/App with spaces"
/usr/bin/python3 - "$REPO_ROOT" "$TEST_ROOT/App with spaces" <<'PY'
from pathlib import Path
import sys, tarfile
with tarfile.open(Path(sys.argv[1]) / 'dist/MDZ-SkyScan-linux.tar.gz') as archive:
    archive.extractall(sys.argv[2], filter='data')
PY
cd "$APP_ROOT"
if bash start.sh >"$TEST_ROOT/before-install.txt" 2>&1; then
  echo 'A fresh Linux download unexpectedly launched without installation.' >&2
  exit 1
fi
/usr/bin/python3 - "$TEST_ROOT/before-install.txt" <<'PY'
from pathlib import Path
import sys
assert 'bash install.sh' in Path(sys.argv[1]).read_text()
PY
mkdir -p .venv
printf '%s\n' 'existing user environment' > .venv/user-file
printf '%s\n' '{"preserve": "existing location"}' > config.json
export XDG_DATA_HOME="$TEST_ROOT/user data"
export XDG_CONFIG_HOME="$TEST_ROOT/user config"
bash install.sh
bash install.sh
/usr/bin/python3 - <<'PY'
from pathlib import Path
import os
from gi.repository import GLib
assert Path('.venv/user-file').read_text().strip() == 'existing user environment'
assert Path('config.json').read_text().strip() == '{"preserve": "existing location"}'
entry = Path(os.environ['XDG_DATA_HOME']) / 'applications/mdz-skyscan.desktop'
text = entry.read_text()
assert 'Exec=/usr/bin/bash "' in text and 'App with spaces' in text
assert 'Terminal=false' in text
keyfile = GLib.KeyFile()
keyfile.load_from_file(str(entry), GLib.KeyFileFlags.NONE)
valid, arguments = GLib.shell_parse_argv(keyfile.get_string('Desktop Entry', 'Exec'))
assert valid and arguments == ['/usr/bin/bash', str(Path.cwd() / 'start.sh')], arguments
PY
MDZ_TEST_PYTHON="$(/usr/bin/python3 linux_setup.py --print-python)"
"$MDZ_TEST_PYTHON" - <<'PY'
import importlib.metadata, gi, sys
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2
import webview
assert sys.prefix != sys.base_prefix
assert importlib.metadata.version('pywebview') == '6.2.1'
print('PASS: downloaded Linux package installs and rechecks its own native environment')
PY
if [ -n "${GITHUB_ENV:-}" ]; then
  printf 'MDZ_TEST_APP_ROOT=%s\nMDZ_TEST_PYTHON=%s\n' "$APP_ROOT" "$MDZ_TEST_PYTHON" >> "$GITHUB_ENV"
fi
