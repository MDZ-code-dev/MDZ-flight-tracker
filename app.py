#!/usr/bin/env python3
"""MDZ Plane Tracker - tiny local web app for Fedora on Nintendo Switch.

No third-party Python packages required.
Live aircraft data: https://api.adsb.lol (ODbL)
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
WEB_DIR = ROOT / "web"
CONFIG_FILE = Path(os.environ.get("MDZ_TRACKER_CONFIG", str(ROOT / "config.json")))
HOST = "127.0.0.1"
PORT = int(os.environ.get("MDZ_TRACKER_PORT", "8765"))
APP_VERSION = "1.0.6"


def frontend_build_id() -> str:
    """Identify the actual bundled UI, including changes within a version."""
    digest = hashlib.sha256(APP_VERSION.encode("utf-8"))
    for asset in sorted(WEB_DIR.rglob("*")):
        if asset.is_file():
            data = asset.read_bytes()
            digest.update(asset.relative_to(WEB_DIR).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(len(data)).encode("ascii"))
            digest.update(b"\0")
            digest.update(data)
    return digest.hexdigest()


BUILD_ID = frontend_build_id()


def health_payload() -> dict:
    return {"ok": True, "app": "mdz-skyscan", "version": APP_VERSION, "build": BUILD_ID}


class TrackerHTTPServer(ThreadingHTTPServer):
    # SO_REUSEADDR can allow a second Windows server to bind an existing port.
    # Exclusivity makes an upgrade collision explicit instead of routing users
    # unpredictably between old and new releases.
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self):
        if sys.platform == "win32":
            self.allow_reuse_address = False
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

DEFAULT_CONFIG = {
    "lat": None,
    "lon": None,
    "radius_nm": 80,
    "refresh_seconds": 5,
}


def load_config() -> dict:
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                cfg.update(saved)
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_config(new_cfg: dict) -> dict:
    cfg = load_config()

    for key in ("lat", "lon"):
        value = new_cfg.get(key, cfg.get(key))
        if value is None or value == "":
            cfg[key] = None
        else:
            cfg[key] = float(value)

    if cfg["lat"] is not None and not -90 <= cfg["lat"] <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    if cfg["lon"] is not None and not -180 <= cfg["lon"] <= 180:
        raise ValueError("Longitude must be between -180 and 180")

    radius = float(new_cfg.get("radius_nm", cfg.get("radius_nm", 80)))
    cfg["radius_nm"] = max(1, min(250, radius))

    refresh = float(new_cfg.get("refresh_seconds", cfg.get("refresh_seconds", 5)))
    cfg["refresh_seconds"] = max(3, min(60, refresh))

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return cfg


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_km = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    km = 2 * r_km * math.asin(math.sqrt(a))
    return km / 1.852


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def direction(deg: float | None) -> str:
    if deg is None:
        return "---"
    names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return names[int((deg + 22.5) // 45) % 8]


def clean_text(value, fallback="---") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def fetch_planes() -> dict:
    cfg = load_config()
    lat, lon = cfg.get("lat"), cfg.get("lon")
    if lat is None or lon is None:
        return {
            "ok": False,
            "needs_location": True,
            "error": "Set a location first",
            "config": cfg,
            "planes": [],
        }

    radius = cfg.get("radius_nm", 80)
    url = f"https://api.adsb.lol/v2/point/{lat}/{lon}/{radius}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MDZ-Plane-Tracker/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ADS-B API HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc
    except (TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("ADS-B API did not return valid data") from exc

    planes = []
    for ac in payload.get("ac", []):
        try:
            alat = float(ac["lat"])
            alon = float(ac["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        dist = haversine_nm(lat, lon, alat, alon)
        brg = bearing_deg(lat, lon, alat, alon)

        alt = ac.get("alt_baro", ac.get("alt_geom"))
        on_ground = str(alt).lower() == "ground"
        if on_ground:
            alt_display = "GROUND"
        elif isinstance(alt, (int, float)):
            alt_display = f"{int(round(alt)):,} FT"
        else:
            alt_display = "---"

        speed = ac.get("gs")
        speed_display = f"{int(round(speed))} KT" if isinstance(speed, (int, float)) else "---"

        track = ac.get("track")
        track_num = float(track) if isinstance(track, (int, float)) else None

        vrate = ac.get("baro_rate", ac.get("geom_rate"))
        if isinstance(vrate, (int, float)):
            if vrate > 100:
                vertical = f"▲ {int(round(vrate))} FPM"
            elif vrate < -100:
                vertical = f"▼ {abs(int(round(vrate)))} FPM"
            else:
                vertical = "LEVEL"
        else:
            vertical = "---"

        db_flags = ac.get("dbFlags", 0)
        try:
            military = bool(int(db_flags) & 1)
        except (TypeError, ValueError):
            military = False

        planes.append({
            "hex": clean_text(ac.get("hex")),
            "callsign": clean_text(ac.get("flight"), "NO CALLSIGN"),
            "registration": clean_text(ac.get("r")),
            "type": clean_text(ac.get("t")),
            "description": clean_text(ac.get("desc")),
            "altitude": alt_display,
            "altitude_raw": alt,
            "speed": speed_display,
            "speed_raw": speed,
            "vertical": vertical,
            "track": track_num,
            "track_direction": direction(track_num),
            "lat": alat,
            "lon": alon,
            "distance_nm": round(dist, 2),
            "bearing": round(brg, 1),
            "bearing_direction": direction(brg),
            "squawk": clean_text(ac.get("squawk")),
            "category": clean_text(ac.get("category")),
            "military": military,
            "seen": ac.get("seen"),
        })

    planes.sort(key=lambda plane: plane["distance_nm"])
    return {
        "ok": True,
        "needs_location": False,
        "updated": int(time.time()),
        "source_now": payload.get("now"),
        "total": len(planes),
        "config": cfg,
        "nearest": planes[0] if planes else None,
        "planes": planes,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, fmt, *args):
        # Keep terminal output clean unless there is a problem.
        return

    def end_headers(self):
        # Every release uses the same local URLs. Never retain stale UI assets.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        # Bundled files may retain timestamps across package upgrades. Serving
        # their contents avoids a stale browser receiving a misleading 304.
        for header in ("If-Modified-Since", "If-None-Match"):
            if header in self.headers:
                del self.headers[header]
        return super().send_head()

    def send_json(self, data, status=HTTPStatus.OK):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/config":
            self.send_json(load_config())
            return
        if path == "/api/planes":
            try:
                self.send_json(fetch_planes())
            except Exception as exc:
                self.send_json({
                    "ok": False,
                    "needs_location": False,
                    "error": str(exc),
                    "config": load_config(),
                    "planes": [],
                }, HTTPStatus.BAD_GATEWAY)
            return
        if path == "/health":
            self.send_json(health_payload())
            return
        super().do_GET()

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/config":
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8")) if body else {}
            cfg = save_config(data)
            self.send_json({"ok": True, "config": cfg})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main(server=None):
    server = server if server is not None else TrackerHTTPServer((HOST, PORT), Handler)
    host, port = server.server_address[:2]
    print(f"MDZ Plane Tracker {APP_VERSION} running at http://{host}:{port}", flush=True)
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
