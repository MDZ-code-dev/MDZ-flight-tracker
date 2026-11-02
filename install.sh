#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/mdz-skyscan.desktop"

mkdir -p "$DESKTOP_DIR"
chmod +x "$ROOT/start.sh"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=MDZ SkyScan
Comment=Pixel aircraft tracker for Nintendo Switch Fedora
Exec=$ROOT/start.sh
Terminal=false
Categories=Network;Utility;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

echo "MDZ SkyScan installed."
echo "Open your app launcher and search: MDZ SkyScan"
