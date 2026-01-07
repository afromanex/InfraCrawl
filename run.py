import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from infracrawl import db
from infracrawl import config
from infracrawl.crawler import Crawler
from infracrawl import configs as config_loader


class ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path)
        if p.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"status\": \"ok\"}")
            return
        if p.path == "/export":
            qs = parse_qs(p.query)
            full = qs.get("full", ["0"])[0] in ("1", "true", "True")
            limit = qs.get("limit", [None])[0]
            try:
                limit_val = int(limit) if limit else None
            except Exception:
                limit_val = None
            pages = db.fetch_pages(full=full, limit=limit_val)
            links = db.fetch_links(limit=limit_val)
            payload = {"pages": pages, "links": links}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
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

    # Load YAML configs and upsert into DB
    try:
        cfgs = config_loader.load_configs_from_dir()
        for c in cfgs:
            cid = db.upsert_config(c["name"], c["root_urls"], c["max_depth"])
            print(f"Loaded config {c['name']} -> id={cid}")
    except Exception as e:
        print(f"Warning: could not load configs: {e}")

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
