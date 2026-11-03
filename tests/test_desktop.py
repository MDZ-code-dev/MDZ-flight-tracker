import errno
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

import app
import desktop


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {
            "MDZ_TRACKER_CONFIG": str(Path(self.tmp.name) / "config.json")
        })
        self.environment.start()
        os.environ.pop("MDZ_TRACKER_PORT", None)

    def tearDown(self):
        self.environment.stop()
        self.tmp.cleanup()

    def test_matching_release_reuses_existing_server(self):
        with patch.object(desktop, "read_health", return_value=app.health_payload()), \
             patch.object(app, "TrackerHTTPServer") as create, \
             patch.object(desktop.webbrowser, "open") as browser:
            desktop.main()
        create.assert_not_called()
        browser.assert_called_once_with(f"http://127.0.0.1:{app.PORT}")

    def test_mismatched_build_gets_new_port_and_opens_that_release(self):
        old = dict(app.health_payload(), build="old-build")
        server = Mock(server_port=41234)
        def start_now(*, target, **kwargs):
            return Mock(start=target)
        with patch.object(desktop, "read_health", side_effect=[old, app.health_payload()]), \
             patch.object(app, "TrackerHTTPServer", return_value=server) as create, \
             patch.object(desktop.threading, "Thread", side_effect=start_now), \
             patch.object(desktop.webbrowser, "open") as browser, \
             patch.object(app, "main") as run:
            desktop.main()
        create.assert_called_once_with((app.HOST, 0), app.Handler)
        browser.assert_called_once_with("http://127.0.0.1:41234")
        run.assert_called_once_with(server)

    def test_explicit_busy_port_reports_how_to_resolve_it(self):
        os.environ["MDZ_TRACKER_PORT"] = str(app.PORT)
        with patch.object(desktop, "read_health", return_value={"ok": True}), \
             patch.object(app, "TrackerHTTPServer") as create, \
             patch.object(desktop.webbrowser, "open") as browser:
            with self.assertRaisesRegex(RuntimeError, "unset MDZ_TRACKER_PORT"):
                desktop.main()
        browser.assert_not_called()
        create.assert_not_called()

    def test_other_bind_errors_are_not_treated_as_old_servers(self):
        with patch.object(desktop, "read_health", return_value=None), \
             patch.object(app, "TrackerHTTPServer", side_effect=PermissionError(errno.EACCES, "denied")):
            with self.assertRaises(PermissionError):
                desktop.main()

    def test_windows_listener_collision_is_distinguished_from_permission_denial(self):
        error = PermissionError(errno.EACCES, "denied")
        error.winerror = 10013
        with patch.object(desktop.socket, "create_connection") as connect:
            self.assertTrue(desktop.occupied_port_error(error, "127.0.0.1", 8765))
        connect.assert_called_once_with(("127.0.0.1", 8765), timeout=0.25)
        with patch.object(desktop.socket, "create_connection", side_effect=ConnectionRefusedError):
            self.assertFalse(desktop.occupied_port_error(error, "127.0.0.1", 8765))

    def test_windows_server_requests_exclusive_port_ownership(self):
        server = app.TrackerHTTPServer.__new__(app.TrackerHTTPServer)
        server.socket = Mock()
        with patch.object(app.sys, "platform", "win32"), \
             patch.object(app.socket, "SO_EXCLUSIVEADDRUSE", 4, create=True), \
             patch.object(ThreadingHTTPServer, "server_bind"):
            server.server_bind()
        self.assertFalse(server.allow_reuse_address)
        server.socket.setsockopt.assert_called_once_with(app.socket.SOL_SOCKET, 4, 1)

    def test_old_server_keeps_running_while_updated_ui_opens_on_new_port(self):
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
        opened = threading.Event()
        urls = []
        fresh_servers = []

        def open_browser(url):
            urls.append(url)
            opened.set()

        def run_fresh(server):
            fresh_servers.append(server)
            server.timeout = 0.1
            deadline = time.monotonic() + 8
            try:
                while not opened.is_set() and time.monotonic() < deadline:
                    server.handle_request()
            finally:
                server.server_close()

        try:
            with patch.object(app, "PORT", old.server_port), \
                 patch.object(app, "main", side_effect=run_fresh), \
                 patch.object(desktop.webbrowser, "open", side_effect=open_browser):
                desktop.main()
            self.assertTrue(opened.wait(1), "Updated release was not opened")
            self.assertNotEqual(urls[0], f"http://127.0.0.1:{old.server_port}")
            self.assertEqual(len(fresh_servers), 1)
            with urllib.request.urlopen(f"http://127.0.0.1:{old.server_port}/health") as response:
                self.assertEqual(json.load(response), {"ok": True})
        finally:
            old.shutdown()
            old.server_close()
            old_thread.join()


if __name__ == "__main__":
    unittest.main()
