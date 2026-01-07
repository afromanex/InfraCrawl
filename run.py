import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.configs import ConfigsRepository
from infracrawl import config
from infracrawl.services.crawler import Crawler
from infracrawl.services.config_service import ConfigService


pages_repo = PagesRepository()
links_repo = LinksRepository()
configs_repo = ConfigsRepository()

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

            if config_name:
                cfg = configs_repo.get_config(config_name)
                if not cfg:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"config not found")
                    return
                cfg_id = cfg.config_id
                root_urls = cfg.root_urls
                cfg_max_depth = cfg.max_depth
                use_depth = depth if depth is not None else cfg_max_depth

                # spawn a single crawl thread which will iterate the config's root URLs
                thread = threading.Thread(target=_start_crawl, args=(None, use_depth, cfg), daemon=True)
                thread.start()

                self.send_response(202)
                self.end_headers()
                self.wfile.write(b"Crawl(s) started for config")
                return

            # fallback: direct URL crawl -> create an ad-hoc config with the URL as root
            use_depth = depth if depth is not None else config.DEFAULT_DEPTH
            from infracrawl.domain.config import CrawlerConfig
            adhoc_cfg = CrawlerConfig(config_id=None, name="adhoc", config_path="<adhoc>", root_urls=[url], max_depth=use_depth)
            thread = threading.Thread(target=_start_crawl, args=(None, use_depth, adhoc_cfg), daemon=True)
            thread.start()

            self.send_response(202)
            self.end_headers()
            self.wfile.write(b"Crawl started")
            return

        self.send_response(404)
        self.end_headers()


def _start_crawl(url: str, depth: int, config: object | None = None):
    print(f"Starting crawl: {url} depth={depth} config={getattr(config, 'name', config)}")
    # Pass repositories explicitly for dependency injection
    crawler = Crawler(
        pages_repo=pages_repo,
        links_repo=links_repo,
        configs_repo=configs_repo
    )
    crawler.crawl(url, max_depth=depth, config=config)
    print(f"Crawl finished: {url}")


def main():

    # Database schema should be initialized elsewhere if needed

    # Load YAML configs and upsert into DB. Remove DB configs not present on disk.
    try:
        config_service = ConfigService(configs_repo=configs_repo)
        config_service.sync_configs_with_disk()
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
