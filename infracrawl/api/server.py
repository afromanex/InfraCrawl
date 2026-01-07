import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from infracrawl.domain.config import CrawlerConfig
from infracrawl.services.config_service import ConfigService


def create_server(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback, host='0.0.0.0', port=8000):
    """Return an HTTPServer instance with control endpoints.

    - `start_crawl_callback(config)` will be called when a crawl is requested.
    """

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
                pages = pages_repo.fetch_pages(full=full, limit=limit_val)
                links = links_repo.fetch_links(limit=limit_val)
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

                # Require a config name and use the ConfigService to load the full CrawlerConfig
                if config_name:
                    cfg = config_service.get_config(config_name)
                    if not cfg:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b"config not found")
                        return
                    use_depth = depth if depth is not None else cfg.max_depth
                    # if depth override provided, clone the config with the override
                    if depth is not None and cfg is not None:
                        cfg = CrawlerConfig(cfg.config_id, cfg.name, cfg.config_path, root_urls=cfg.root_urls, max_depth=use_depth, robots=cfg.robots, refresh_days=cfg.refresh_days)
                    threading.Thread(target=start_crawl_callback, args=(cfg,), daemon=True).start()
                    self.send_response(202)
                    self.end_headers()
                    self.wfile.write(b"Crawl(s) started for config")
                    return

            if self.path == "/reload":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    data = json.loads(body.decode("utf-8"))
                    config_name = data.get("config")
                    if not config_name:
                        raise ValueError("missing config")
                except Exception as e:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(str(e).encode())
                    return

                cfg = config_service.get_config(config_name)
                if not cfg:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"config not found")
                    return

                # Delete pages and links associated with this config
                try:
                    page_ids = pages_repo.get_page_ids_by_config(cfg.config_id)
                    deleted_links = 0
                    deleted_pages = 0
                    if page_ids:
                        deleted_links = links_repo.delete_links_for_page_ids(page_ids)
                        deleted_pages = pages_repo.delete_pages_by_ids(page_ids)
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f"error clearing data: {e}".encode())
                    return

                # Start crawl asynchronously
                threading.Thread(target=start_crawl_callback, args=(cfg,), daemon=True).start()
                self.send_response(202)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {"status": "reloading", "deleted_pages": deleted_pages, "deleted_links": deleted_links}
                self.wfile.write(json.dumps(resp).encode("utf-8"))
                return

                # Do not accept direct URLs here — only config names are supported
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"/crawl only accepts a config name")
                return

            self.send_response(404)
            self.end_headers()

    server = HTTPServer((host, port), ControlHandler)
    return server
