#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x /usr/bin/python3 ]; then
  echo "Install your distribution's Python 3 package, then run bash install.sh again." >&2
  exit 1
fi
# Read-only helper commands must not create an application shortcut.
for argument in "$@"; do
  case "$argument" in
    --help|-h|--check|--print-python)
      exec /usr/bin/python3 -I "$ROOT/linux_setup.py" "$@"
      ;;
  esac
done
/usr/bin/python3 -I "$ROOT/linux_setup.py" "$@"

# Write the desktop shortcut only after native imports have been verified.
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/mdz-skyscan.desktop"
mkdir -p "$DESKTOP_DIR"
chmod +x "$ROOT/start.sh"
MDZ_INSTALL_ROOT="$ROOT" MDZ_DESKTOP_FILE="$DESKTOP_FILE" /usr/bin/python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ['MDZ_INSTALL_ROOT'])
destination = Path(os.environ['MDZ_DESKTOP_FILE'])
def quote(value):
    # Escape the Exec argument first, then the desktop-file string layer.
    # Percent signs are field codes, independent of shell quoting.
    argument = '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
    return argument.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
text = '\n'.join([
    '[Desktop Entry]', 'Type=Application', 'Name=MDZ SkyScan',
    'Comment=Live aircraft tracker',
    'Exec=/usr/bin/bash ' + quote(root / 'start.sh'),
    'Terminal=false', 'Categories=Network;Utility;', 'StartupNotify=true', '',
])
destination.write_text(text, encoding='utf-8')
destination.chmod(0o755)
PY
printf '%s\n' "MDZ SkyScan is installed. Open it from your application launcher."
