import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from infracrawl import db
from infracrawl import config
from infracrawl.crawler import Crawler


class ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"status\": \"ok\"}")
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/crawl":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                url = data.get("url")
                depth = data.get("depth", config.DEFAULT_DEPTH)
                if not url:
                    raise ValueError("missing url")
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

            # spawn crawl in separate thread
            thread = threading.Thread(target=_start_crawl, args=(url, depth), daemon=True)
            thread.start()

            self.send_response(202)
            self.end_headers()
            self.wfile.write(b"Crawl started")
            return

        self.send_response(404)
        self.end_headers()


def _start_crawl(url: str, depth: int):
    print(f"Starting crawl: {url} depth={depth}")
    crawler = Crawler()
    crawler.crawl(url, max_depth=depth)
    print(f"Crawl finished: {url}")


def main():
    print("Initializing database (if available)...")
    try:
        db.init_db()
        print("Schema initialized or already present.")
    except Exception as e:
        print(f"Warning: could not initialize DB: {e}")

    # Start control HTTP server
    server_port = 8000
    server = HTTPServer(("0.0.0.0", server_port), ControlHandler)

    def serve():
        print(f"Control server listening on 0.0.0.0:{server_port}")
        server.serve_forever()

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    # Heartbeat loop
    try:
        while True:
            print("InfraCrawl daemon heartbeat")
            time.sleep(30)
    except KeyboardInterrupt:
        print("Shutting down")
        server.shutdown()


if __name__ == '__main__':
    main()
