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
            return json.loads(response.read(), parse_constant=lambda value: self.fail(f"Invalid JSON number: {value}"))

    def save(self, data):
        request = urllib.request.Request(self.url + "/api/config", json.dumps(data).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def test_bundled_ui_and_health(self):
        self.assertEqual(self.get("/health"), app.health_payload())
        for path, marker in [("/", b"MDZ SKYSCAN"), ("/native.js", b"mdzFetch"),
                             ("/silhouettes.js", b"aircraftProfile"), ("/app.js", b"aircraftLabel")]:
            with urllib.request.urlopen(self.url + path) as response:
                self.assertIn(marker, response.read())

    def test_static_assets_are_fresh_even_with_old_cache_conditions(self):
        request = urllib.request.Request(self.url + "/app.js", headers={
            "If-Modified-Since": "Fri, 01 Jan 2100 00:00:00 GMT",
            "If-None-Match": '"old-release"',
        })
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertIn(b"aircraftLabel", response.read())

    def test_frontend_identity_changes_when_asset_contents_change(self):
        web = Path(self.tmp.name) / "web"
        web.mkdir()
        asset = web / "app.js"
        asset.write_text("old frontend", encoding="utf-8")
        with patch.object(app, "WEB_DIR", web):
            before = app.frontend_build_id()
            asset.write_text("new frontend", encoding="utf-8")
            self.assertNotEqual(app.frontend_build_id(), before)

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
            {"hex": "c00123", "lat": 44, "lon": -79.38, "alt_baro": "ground",
             "t": "CL35", "flight": " JET42 ", "r": "C-GJET", "desc": "Bombardier Challenger 350"},
            {"hex": "c00456", "lat": 43.66, "lon": -79.38, "t": "B738", "flight": " ROU1357 ",
             "r": "C-F737", "desc": "Boeing 737-800", "dbFlags": 1, "seen": 1, "seen_pos": 2},
            {"hex": "missing-position"},
        ]}
        data = self.planes_fixture(payload)
        self.assertTrue(data["ok"])
        self.assertEqual(data["total"], 2)
        nearest = data["nearest"]
        self.assertEqual((nearest["hex"], nearest["type"], nearest["callsign"], nearest["registration"], nearest["description"]),
                         ("c00456", "B738", "ROU1357", "C-F737", "Boeing 737-800"))
        self.assertTrue(nearest["military"])
        farther = data["planes"][1]
        self.assertEqual((farther["hex"], farther["type"], farther["callsign"], farther["registration"]),
                         ("c00123", "CL35", "JET42", "C-GJET"))
        self.assertEqual(farther["altitude"], "GROUND")

    def planes_fixture(self, payload):
        # Patch only the remote request: keep local HTTP calls real.
        original = urllib.request.urlopen
        def remote_or_local(request, *args, **kwargs):
            url = request.full_url if isinstance(request, urllib.request.Request) else request
            if url.startswith("https://api.adsb.lol/"):
                return io.BytesIO(json.dumps(payload).encode())
            return original(request, *args, **kwargs)
        with patch.object(app.urllib.request, "urlopen", side_effect=remote_or_local):
            return self.get("/api/planes")

    def test_invalid_stale_and_outside_contacts_cannot_be_nearest(self):
        self.save({"lat": 43.65, "lon": -79.38, "radius_nm": 80})
        data = self.planes_fixture({"ac": [
            {"hex": "current", "lat": 43.66, "lon": -79.38, "t": "B738"},
            {"hex": "old-message", "lat": 43.65001, "lon": -79.38, "seen": 90.1},
            {"hex": "old-position", "lat": 43.65002, "lon": -79.38, "seen": 1, "seen_pos": 91},
            {"hex": "nan", "lat": float("nan"), "lon": -79.38},
            {"hex": "infinite", "lat": 43.65, "lon": float("inf")},
            {"hex": "invalid-lat", "lat": 91, "lon": -79.38},
            {"hex": "invalid-lon", "lat": 43.65, "lon": 181},
            {"hex": "bool-lat", "lat": True, "lon": -79.38},
            {"hex": "outside-radius", "lat": 45.1, "lon": -79.38},
            None,
        ]})
        self.assertEqual([plane["hex"] for plane in data["planes"]], ["current"])
        self.assertEqual(data["nearest"]["type"], "B738")

    def test_unknown_ages_and_threshold_age_remain_eligible(self):
        self.save({"lat": 43.65, "lon": -79.38})
        data = self.planes_fixture({"ac": [
            {"hex": "no-age", "lat": 43.66, "lon": -79.38},
            {"hex": "unknown-age", "lat": 43.67, "lon": -79.38, "seen": "unknown", "seen_pos": None},
            {"hex": "boundary-age", "lat": 43.68, "lon": -79.38, "seen": 90, "seen_pos": 90},
        ]})
        self.assertEqual([plane["hex"] for plane in data["planes"]], ["no-age", "unknown-age", "boundary-age"])
        self.assertEqual(data["nearest"]["hex"], "no-age")
        self.assertIsNone(data["planes"][1]["seen"])

    def test_bad_optional_telemetry_is_unknown_and_feed_is_valid_json(self):
        self.save({"lat": 43.65, "lon": -79.38})
        data = self.planes_fixture({"now": float("inf"), "ac": [
            {"hex": "nan-values", "lat": 43.66, "lon": -79.38, "alt_baro": float("nan"),
             "gs": float("inf"), "track": float("-inf"), "baro_rate": float("nan"),
             "seen": float("nan"), "seen_pos": float("inf"), "dbFlags": float("inf")},
            {"hex": "wrapped-heading", "lat": 43.67, "lon": -79.38, "track": -90},
            {"hex": "extra-revolution", "lat": 43.68, "lon": -79.38, "track": 450},
        ]})
        self.assertTrue(data["ok"])
        self.assertEqual(data["total"], 3)
        invalid = data["nearest"]
        for field in ("altitude_raw", "speed_raw", "track", "seen", "seen_pos"):
            self.assertIsNone(invalid[field], field)
        for field in ("altitude", "speed", "vertical", "track_direction"):
            self.assertEqual(invalid[field], "---", field)
        self.assertFalse(invalid["military"])
        self.assertIsNone(data["source_now"])
        self.assertEqual((data["planes"][1]["track"], data["planes"][1]["track_direction"]), (270, "W"))
        self.assertEqual((data["planes"][2]["track"], data["planes"][2]["track_direction"]), (90, "E"))

    def test_nearest_uses_unrounded_distance(self):
        self.save({"lat": 43.65, "lon": -79.38})
        data = self.planes_fixture({"ac": [
            {"hex": "farther", "lat": 43.65002, "lon": -79.38, "t": "CL35"},
            {"hex": "closer", "lat": 43.65001, "lon": -79.38, "t": "B738"},
        ]})
        self.assertEqual(data["planes"][0]["distance_nm"], data["planes"][1]["distance_nm"])
        self.assertEqual(data["nearest"]["hex"], "closer")

    def test_conflicting_source_identity_is_not_replaced_with_a_guess(self):
        self.save({"lat": 43.65, "lon": -79.38})
        data = self.planes_fixture({"ac": [{"hex": "conflict", "lat": 43.66, "lon": -79.38,
            "t": "B738", "desc": "Bombardier Challenger 350", "flight": "CL350", "r": "C-TEST"}]})
        self.assertEqual((data["nearest"]["type"], data["nearest"]["description"], data["nearest"]["callsign"]),
                         ("B738", "Bombardier Challenger 350", "CL350"))


if __name__ == "__main__":
    unittest.main()
