#!/usr/bin/env python3
"""Portable desktop entry point; no third-party runtime packages required."""
import os
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def main():
    if "MDZ_TRACKER_CONFIG" not in os.environ:
        base = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
                if sys.platform == "win32" else
                Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")))
        os.environ["MDZ_TRACKER_CONFIG"] = str(base / "mdz-skyscan" / "config.json")

    import app
    url = f"http://127.0.0.1:{app.PORT}"

    def ready():
        try:
            with urllib.request.urlopen(url + "/health", timeout=0.4) as response:
                return response.read() == b'{"ok": true}'
        except OSError:
            return False

    if ready():
        webbrowser.open(url)
        return

    def open_when_ready():
        for _ in range(50):
            if ready():
                webbrowser.open(url)
                return
            time.sleep(0.1)

    threading.Thread(target=open_when_ready, daemon=True).start()
    app.main()


if __name__ == "__main__":
    main()
