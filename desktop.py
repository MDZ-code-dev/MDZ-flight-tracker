#!/usr/bin/env python3
"""Portable desktop entry point; no third-party runtime packages required."""
import os
import errno
import json
import socket
import sys
import threading
import time
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path


def read_health(url):
    try:
        request = urllib.request.Request(url + "/health", headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=0.4) as response:
            try:
                data = json.load(response)
                return data if isinstance(data, dict) else {}
            except ValueError:
                return {}  # A listener replied, but it is not this app's health endpoint.
    except urllib.error.HTTPError:
        return {}
    except OSError:
        return None


def same_build(observed, expected):
    return (isinstance(observed, dict) and observed.get("ok") is True
            and all(observed.get(key) == expected[key] for key in ("app", "version", "build")))


def occupied_port_error(error, host, port):
    if error.errno == errno.EADDRINUSE or getattr(error, "winerror", None) == 10048:
        return True
    # Windows exclusive binding may report access denied when another process
    # owns the address. Confirm a listener before treating it as a collision;
    # genuine permissions/excluded-port errors must still be reported.
    if getattr(error, "winerror", None) == 10013:
        try:
            with socket.create_connection((host, port), timeout=0.25):
                return True
        except OSError:
            pass
    return False


def main():
    if "MDZ_TRACKER_CONFIG" not in os.environ:
        base = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
                if sys.platform == "win32" else
                Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")))
        os.environ["MDZ_TRACKER_CONFIG"] = str(base / "mdz-skyscan" / "config.json")

    import app
    expected = app.health_payload()
    url = f"http://127.0.0.1:{app.PORT}"
    observed = read_health(url) if app.PORT else None
    if same_build(observed, expected):
        webbrowser.open(url)
        return

    def fresh_port_server():
        if "MDZ_TRACKER_PORT" in os.environ:
            raise RuntimeError(
                f"MDZ_TRACKER_PORT={app.PORT} is already in use by another app or an older SkyScan. "
                "Close that server, choose a different port, or unset MDZ_TRACKER_PORT."
            )
        # Opening an old process would silently show its old UI. Leave it alone
        # and bind a new port before opening this release in the browser.
        return app.TrackerHTTPServer((app.HOST, 0), app.Handler)

    if observed is not None:
        # Proactive selection also avoids Windows SO_REUSEADDR ambiguities.
        server = fresh_port_server()
    else:
        try:
            server = app.TrackerHTTPServer((app.HOST, app.PORT), app.Handler)
        except OSError as error:
            if not occupied_port_error(error, app.HOST, app.PORT):
                raise
            # A matching instance might have started between the probe and bind.
            if same_build(read_health(url), expected):
                webbrowser.open(url)
                return
            server = fresh_port_server()
    url = f"http://127.0.0.1:{server.server_port}"

    def open_when_ready():
        for _ in range(50):
            if same_build(read_health(url), expected):
                webbrowser.open(url)
                return
            time.sleep(0.1)

    threading.Thread(target=open_when_ready, daemon=True).start()
    app.main(server)


if __name__ == "__main__":
    main()
