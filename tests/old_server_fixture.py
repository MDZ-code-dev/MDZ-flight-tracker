"""A legacy local server for the packaged Windows upgrade regression check."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class LegacyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        health = self.path.split("?", 1)[0] == "/health"
        body = b'{"ok": true}' if health else b"OLD RELEASE WITHOUT SILHOUETTE"
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if health else "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-MDZ-Old-Fixture", "1")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), LegacyHandler)
    print(f"Legacy SkyScan fixture ready on {server.server_port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
