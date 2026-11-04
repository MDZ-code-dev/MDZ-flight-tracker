#!/usr/bin/env python3
"""Exercise the real GTK desktop window under Xvfb, including backend cleanup.

Run with a Python venv created using --system-site-packages so that Ubuntu's
PyGObject and WebKit2GTK packages are available, for example:
    xvfb-run -a .venv/bin/python tests/smoke_linux_window.py
This is deliberately separate from unittest discovery: it needs a display and
the native desktop dependencies in desktop-requirements.txt.
"""
import importlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import traceback
from unittest import mock
from urllib.parse import urlsplit
from urllib.request import urlopen


ROOT = Path(os.environ.get("MDZ_TEST_APP_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(ROOT))

PLANE = {
    "callsign": "SKY747", "hex": "abc123", "registration": "N747",
    "type": "B744", "description": "BOEING 747-400", "squawk": "1200",
    "altitude": "12,000 FT", "speed": "250 KT", "vertical": "LEVEL",
    "track": 238, "track_direction": "SW", "distance_nm": 4.2,
    "bearing": 173, "bearing_direction": "S", "military": False,
    "lat": 43.66, "lon": -79.38,
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class NativeWindowProbe:
    """Delegate to real pywebview, adding checks inside its GTK event loop."""

    def __init__(self, webview):
        self.webview = webview
        self.window = None
        self.url = None
        self.loaded = threading.Event()
        self.finished = threading.Event()
        self.failure = None

    def __getattr__(self, name):
        return getattr(self.webview, name)

    def create_window(self, title, url, **kwargs):
        require(title == "MDZ SkyScan", f"Unexpected window title: {title!r}")
        self.url = url
        self.window = self.webview.create_window(title, url, **kwargs)
        self.window.events.loaded += self.on_loaded
        return self.window

    def on_loaded(self, *args):
        self.loaded.set()

    def start(self, **kwargs):
        require(kwargs.get("gui") == "gtk", "Linux must use the GTK renderer")
        require(kwargs.get("debug") is False, "The app must disable GUI debugging")
        self.webview.start(func=self.check_window, **kwargs)

    def wait_for_js(self, script, description, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.window.evaluate_js(script):
                return
            time.sleep(0.05)
        raise AssertionError(f"Timed out waiting for {description}")

    def check_window(self):
        try:
            require(self.loaded.wait(30), "GTK window did not finish loading")
            current_url = self.window.get_current_url()
            location = urlsplit(current_url)
            require(location.scheme == "http" and location.hostname == "127.0.0.1",
                    f"Native window loaded an unexpected URL: {current_url!r}")
            require(location.netloc == urlsplit(self.url).netloc,
                    "Window did not load the backend owned by this launcher")
            with urlopen(self.url + "/health", timeout=3) as response:
                health = json.load(response)
            require(health.get("ok") is True and health.get("app") == "mdz-skyscan",
                    f"Unexpected health response: {health!r}")
            require(health.get("version") == "1.0.10", f"Wrong app version: {health!r}")
            require(len(health.get("build", "")) == 64, "Health response has no build hash")

            # Wait for startup's asynchronous config read before closing its
            # first-run modal. No location is saved and no live feed is needed.
            self.wait_for_js("document.getElementById('settingsModal').classList.contains('open')",
                             "first-run settings")
            self.window.evaluate_js("closeSettings(); renderNearest(" + json.dumps(PLANE) + ", 1)")
            fonts_ready = threading.Event()
            self.window.evaluate_js("document.fonts.ready.then(() => true)",
                                    callback=lambda result: fonts_ready.set() if result is True else None)
            require(fonts_ready.wait(15), "document.fonts.ready did not resolve")
            result = self.window.evaluate_js("""(() => {
                const shape = document.getElementById('aircraftSilhouette');
                const visual = document.getElementById('aircraftVisual');
                const rect = visual.getBoundingClientRect();
                const length = shape.getTotalLength(), matrix = shape.getScreenCTM();
                const points = Array.from({length: 301}, (_, i) =>
                    shape.getPointAtLength(length * i / 300).matrixTransform(matrix));
                return {
                    fontLoaded: Array.from(document.fonts).some(font =>
                        font.family.replace(/["']/g, '') === 'SkyScan Pixel' && font.status === 'loaded'),
                    fontUsed: getComputedStyle(document.body).fontFamily.includes('SkyScan Pixel'),
                    version: document.getElementById('appVersion').textContent,
                    model: document.getElementById('aircraftVisualType').textContent,
                    path: shape.getAttribute('d'), transform: shape.getAttribute('transform'),
                    length: length, visible: !visual.classList.contains('is-empty') &&
                        getComputedStyle(visual).display !== 'none',
                    svgHeight: document.querySelector('.aircraft-visual-svg').getBoundingClientRect().height,
                    insideVisual: points.every(point => point.x >= rect.left && point.x <= rect.right &&
                        point.y >= rect.top && point.y <= rect.bottom),
                    insideWindow: points.every(point => point.x >= 0 && point.x <= innerWidth &&
                        point.y >= 0 && point.y <= innerHeight)
                };
            })()""")
            require(result["fontLoaded"] and result["fontUsed"],
                    f"Bundled pixel font did not load in GTK: {result!r}")
            require(result["version"] == "v1.0.10", "Window is showing an old UI version")
            require(result["model"] == "B744", "Nearest mode did not show the aircraft model")
            require(result["path"] and result["length"] > 0, "Aircraft silhouette is empty")
            require(result["transform"] == "rotate(238 120 120)", "Silhouette heading is wrong")
            require(result["visible"] and result["svgHeight"] >= 80 and
                    result["insideVisual"] and result["insideWindow"],
                    f"Aircraft silhouette is hidden or clipped in GTK: {result!r}")

            self.window.evaluate_js("switchMode()")
            self.wait_for_js("document.getElementById('modeBtn').textContent === 'MODE: RADAR' && "
                             "document.getElementById('radar').width > 100 && "
                             "document.getElementById('radar').height > 100", "radar canvas")
            self.window.evaluate_js("switchMode()")
            self.wait_for_js("document.getElementById('modeBtn').textContent === 'MODE: NEAREST' && "
                             "document.getElementById('nearestMode').classList.contains('active') && "
                             "document.getElementById('aircraftSilhouette').getAttribute('d').length > 0",
                             "return to nearest mode")
        except BaseException as error:
            self.failure = error
            traceback.print_exc()
        finally:
            try:
                self.window.destroy()
            except BaseException as error:
                self.failure = self.failure or error
                traceback.print_exc()
            self.finished.set()


def ensure_backend_stopped(url):
    location = urlsplit(url)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((location.hostname, location.port), timeout=0.2):
                pass
        except OSError:
            return
        time.sleep(0.05)
    raise AssertionError("Closing the GTK app left its backend listening")


def watchdog_expired():
    print("::error::Linux native smoke exceeded 75 seconds; the GTK window or shutdown hung",
          file=sys.stderr, flush=True)
    os._exit(1)


def main():
    require(sys.platform.startswith("linux"), "This smoke test requires Linux GTK")
    require(os.environ.get("DISPLAY"), "A display is required; run this test with xvfb-run -a")
    desktop = importlib.import_module("desktop")
    probe = NativeWindowProbe(importlib.import_module("webview"))
    watchdog = threading.Timer(75, watchdog_expired)
    watchdog.daemon = True
    watchdog.start()
    try:
        with tempfile.TemporaryDirectory(prefix="mdz-native-gtk-") as config_dir:
            environment = dict(os.environ)
            environment.pop("MDZ_TRACKER_PORT", None)
            environment.pop("MDZ_DESKTOP_STATE_FILE", None)
            environment["MDZ_TRACKER_CONFIG"] = str(Path(config_dir) / "config.json")
            with mock.patch.dict(os.environ, environment, clear=True), \
                    mock.patch.object(desktop, "load_webview", return_value=probe), \
                    mock.patch("webbrowser.open", side_effect=AssertionError("External browser opened")):
                desktop.main()
        require(probe.window is not None, "Launcher did not create a native window")
        require(probe.finished.is_set(), "GTK exited before the window checks ran")
        if probe.failure:
            raise probe.failure
        ensure_backend_stopped(probe.url)
        print("PASS: real GTK window, bundled pixel font, visible B744 silhouette, radar, "
              "v1.0.10 health, and backend shutdown", flush=True)
    finally:
        watchdog.cancel()


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        print(f"::error::Linux native smoke failed: {error}", file=sys.stderr, flush=True)
        raise
