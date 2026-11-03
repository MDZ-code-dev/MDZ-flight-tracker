import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

import app
import desktop


class NativeLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            "MDZ_TRACKER_CONFIG": str(Path(self.tmp.name) / "config.json")
        })
        self.environment.start()
        os.environ.pop("MDZ_TRACKER_PORT", None)
        os.environ.pop("MDZ_DESKTOP_STATE_FILE", None)
        os.environ.pop("MDZ_NATIVE_TEST_PORT", None)
        self.view = Mock()
        self.view.settings = {}
        self.urls = []
        self.view.create_window.side_effect = lambda title, url, **kwargs: self.urls.append(url)

    def tearDown(self):
        self.environment.stop()
        self.tmp.cleanup()

    def assert_stopped(self, url):
        with self.assertRaises(OSError):
            urllib.request.urlopen(url + "/health", timeout=0.5)

    def test_real_backend_is_owned_by_window_and_stops_on_close(self):
        observed = []
        def window_loop(**kwargs):
            with urllib.request.urlopen(self.urls[0] + "/health") as response:
                observed.append(json.load(response))
        self.view.start.side_effect = window_loop
        with patch.object(desktop, "load_webview", return_value=self.view), \
             patch("webbrowser.open") as browser:
            desktop.main()
        self.assertEqual(observed, [app.health_payload()])
        self.assertEqual(self.view.create_window.call_args.args[0], "MDZ SkyScan")
        self.assertEqual(self.view.start.call_args.kwargs["debug"], False)
        browser.assert_not_called()
        self.assert_stopped(self.urls[0])

    def test_gui_failure_still_stops_owned_backend(self):
        self.view.start.side_effect = RuntimeError("Renderer failed")
        with patch.object(desktop, "load_webview", return_value=self.view):
            with self.assertRaisesRegex(RuntimeError, "Renderer failed"):
                desktop.main()
        self.assert_stopped(self.urls[0])

    def test_missing_gui_dependency_does_not_start_server_or_browser(self):
        with patch.object(desktop, "load_webview", side_effect=RuntimeError("missing GUI")), \
             patch.object(app, "TrackerHTTPServer") as create, patch("webbrowser.open") as browser:
            with self.assertRaisesRegex(RuntimeError, "missing GUI"):
                desktop.main()
        create.assert_not_called()
        browser.assert_not_called()

    def test_dependency_error_explains_installation(self):
        with patch.object(desktop.importlib, "import_module", side_effect=ImportError("webview")):
            with self.assertRaisesRegex(RuntimeError, "desktop-requirements.txt"):
                desktop.load_webview()

    def test_window_never_reuses_an_old_server(self):
        class OldHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b'{"ok": true}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        old = ThreadingHTTPServer(("127.0.0.1", 0), OldHandler)
        old_thread = threading.Thread(target=old.serve_forever, daemon=True)
        old_thread.start()
        try:
            with patch.object(app, "PORT", old.server_port), \
                 patch.object(desktop, "load_webview", return_value=self.view):
                desktop.main()
            self.assertNotEqual(self.urls[0], f"http://127.0.0.1:{old.server_port}")
            self.assert_stopped(self.urls[0])
            with urllib.request.urlopen(f"http://127.0.0.1:{old.server_port}/health") as response:
                self.assertEqual(json.load(response), {"ok": True})
        finally:
            old.shutdown()
            old.server_close()
            old_thread.join()

    def test_explicit_busy_port_does_not_take_over_existing_app(self):
        old = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        try:
            os.environ["MDZ_TRACKER_PORT"] = str(old.server_port)
            with patch.object(app, "PORT", old.server_port), \
                 patch.object(desktop, "load_webview", return_value=self.view):
                with self.assertRaisesRegex(RuntimeError, "unset MDZ_TRACKER_PORT"):
                    desktop.main()
            self.view.create_window.assert_not_called()
        finally:
            old.server_close()

    def test_optional_runtime_diagnostics_and_windows_renderer(self):
        state = Path(self.tmp.name) / "runtime.json"
        os.environ["MDZ_DESKTOP_STATE_FILE"] = str(state)
        with patch.object(desktop, "load_webview", return_value=self.view), \
             patch.object(desktop, "require_windows_runtime"), \
             patch.object(desktop.sys, "platform", "win32"):
            desktop.main()
        data = json.loads(state.read_text())
        self.assertEqual(data["url"], self.urls[0])
        self.assertEqual(data["pid"], os.getpid())
        self.assertEqual(data["renderer"], "edgechromium")
        self.assertEqual(data["version"], app.APP_VERSION)
        self.view.start.assert_called_once_with(gui="edgechromium", debug=False)
        self.assert_stopped(self.urls[0])

    def test_windows_missing_runtime_cannot_fall_back_to_legacy_renderer(self):
        with patch.object(desktop, "load_webview", return_value=self.view), \
             patch.object(desktop.sys, "platform", "win32"), \
             patch.object(desktop, "require_windows_runtime", side_effect=RuntimeError("WebView2 required")), \
             patch.object(app, "TrackerHTTPServer") as server:
            with self.assertRaisesRegex(RuntimeError, "WebView2 required"):
                desktop.main()
        server.assert_not_called()
        self.view.create_window.assert_not_called()

    def test_native_debugging_is_disabled_outside_explicit_ci(self):
        os.environ["MDZ_NATIVE_TEST_PORT"] = "12345"
        os.environ["MDZ_DESKTOP_STATE_FILE"] = str(Path(self.tmp.name) / "state.json")
        os.environ["CI"] = "false"
        self.assertFalse(desktop.configure_native_test(self.view))
        self.assertEqual(self.view.settings, {})
        os.environ["CI"] = "true"
        self.assertTrue(desktop.configure_native_test(self.view))
        self.assertEqual(self.view.settings["REMOTE_DEBUGGING_PORT"], 12345)
        self.assertFalse(self.view.settings["OPEN_DEVTOOLS_IN_DEBUG"])


if __name__ == "__main__":
    unittest.main()
