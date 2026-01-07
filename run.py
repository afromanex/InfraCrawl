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
            payload = {
                "pages": [p.__dict__ for p in pages],
                "links": [l.__dict__ for l in links]
            }
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
                # support either a direct URL or a config name
                url = data.get("url")
                config_name = data.get("config")
                depth = data.get("depth", None)
                if not (url or config_name):
                    raise ValueError("missing url or config")
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode())
                return

            if config_name:
                cfg = db.get_config(config_name)
                if not cfg:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"config not found")
                    return
                cfg_id = cfg["config_id"]
                root_urls = cfg["root_urls"]
                cfg_max_depth = cfg["max_depth"]
                use_depth = depth if depth is not None else cfg_max_depth

                # spawn crawl threads for each root URL
                for ru in root_urls:
                    thread = threading.Thread(target=_start_crawl, args=(ru, use_depth, cfg_id), daemon=True)
                    thread.start()

                self.send_response(202)
                self.end_headers()
                self.wfile.write(b"Crawl(s) started for config")
                return

            # fallback: direct URL crawl
            use_depth = depth if depth is not None else config.DEFAULT_DEPTH
            thread = threading.Thread(target=_start_crawl, args=(url, use_depth, None), daemon=True)
            thread.start()

            self.send_response(202)
            self.end_headers()
            self.wfile.write(b"Crawl started")
            return

        self.send_response(404)
        self.end_headers()


def _start_crawl(url: str, depth: int, config_id: int | None = None):
    print(f"Starting crawl: {url} depth={depth} config_id={config_id}")
    crawler = Crawler()
    crawler.crawl(url, max_depth=depth, config_id=config_id)
    print(f"Crawl finished: {url}")


def main():
    print("Initializing database (if available)...")
    try:
        db.init_db()
        print("Schema initialized or already present.")
    except Exception as e:
        print(f"Warning: could not initialize DB: {e}")

    # Load YAML configs and upsert into DB. Remove DB configs not present on disk.
    try:
        cfgs = config_loader.load_configs_from_dir()
        loaded_names = set()
        for c in cfgs:
            cid = db.upsert_config(
                c["name"], c["root_urls"], c["max_depth"], robots=c.get("robots", True), refresh_days=c.get("refresh_days")
            )
            loaded_names.add(c["name"])
            print(f"Loaded config {c['name']} -> id={cid}")

        # Remove any configs in DB that are not present in the configs directory
        existing_configs = db.list_configs()
        existing_names = set(c.name for c in existing_configs)
        to_remove = existing_names - loaded_names
        for name in to_remove:
            db.delete_config(name)
            print(f"Removed DB config not present on disk: {name}")
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
