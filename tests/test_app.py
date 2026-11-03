import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import app


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = Path(self.tmp.name) / "settings/config.json"
        self.patch = patch.object(app, "CONFIG_FILE", self.config)
        self.patch.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.patch.stop()
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.url + path) as response:
            return json.load(response)

    def save(self, data):
        request = urllib.request.Request(self.url + "/api/config", json.dumps(data).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def test_bundled_ui_and_health(self):
        self.assertEqual(self.get("/health"), {"ok": True})
        for path, marker in [("/", b"MDZ SKYSCAN"), ("/native.js", b"mdzFetch"), ("/app.js", b"aircraftLabel")]:
            with urllib.request.urlopen(self.url + path) as response:
                self.assertIn(marker, response.read())

    def test_location_required(self):
        self.assertIsNone(self.get("/api/config")["lat"])
        self.assertTrue(self.get("/api/planes")["needs_location"])

    def test_settings_persist_outside_app_directory(self):
        result = self.save({"lat": 43.65, "lon": -79.38, "radius_nm": 999, "refresh_seconds": 1})
        self.assertTrue(result["ok"])
        self.assertEqual(self.get("/api/config")["radius_nm"], 250)
        self.assertEqual(json.loads(self.config.read_text())["refresh_seconds"], 3)

    def test_invalid_location_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.save({"lat": 91})
        self.assertEqual(error.exception.code, 400)
        self.assertFalse(self.config.exists())

    def test_live_payload_normalization(self):
        self.save({"lat": 43.65, "lon": -79.38})
        payload = {"ac": [
            {"hex": "far", "lat": 44, "lon": -79.38, "alt_baro": "ground"},
            {"hex": "near", "lat": 43.66, "lon": -79.38, "t": "B747", "flight": " TEST ", "dbFlags": 1},
            {"hex": "missing-position"},
        ]}
        # Patch only the remote request: keep local HTTP calls real.
        original = urllib.request.urlopen
        def remote_or_local(request, *args, **kwargs):
            url = request.full_url if isinstance(request, urllib.request.Request) else request
            if url.startswith("https://api.adsb.lol/"):
                return io.BytesIO(json.dumps(payload).encode())
            return original(request, *args, **kwargs)
        with patch.object(app.urllib.request, "urlopen", side_effect=remote_or_local):
            data = self.get("/api/planes")
        self.assertTrue(data["ok"])
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["nearest"]["type"], "B747")
        self.assertEqual(data["nearest"]["callsign"], "TEST")
        self.assertTrue(data["nearest"]["military"])
        self.assertEqual(data["planes"][1]["altitude"], "GROUND")


if __name__ == "__main__":
    unittest.main()
