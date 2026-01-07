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
    # Pass repositories explicitly for dependency injection
    crawler = Crawler(
        pages_repo=pages_repo,
        links_repo=links_repo,
        configs_repo=configs_repo
    )
    crawler.crawl(url, max_depth=depth, config_id=config_id)
    print(f"Crawl finished: {url}")


def main():

    # Database schema should be initialized elsewhere if needed

    # Load YAML configs and upsert into DB. Remove DB configs not present on disk.
    try:
        config_service = ConfigService(configs_repo=configs_repo)
        config_files = config_service.list_configs()
        loaded_names = set()
        # Upsert configs from files (by name and config_path)
        import os
        configs_dir = os.path.join(os.getcwd(), "configs")
        for fname in os.listdir(configs_dir):
            if not (fname.endswith(".yml") or fname.endswith(".yaml")):
                continue
            full_path = os.path.join(configs_dir, fname)
            try:
                import yaml
                with open(full_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                name = data.get("name")
                if not name:
                    continue
                from infracrawl.domain import CrawlerConfig
                config_obj = CrawlerConfig(
                    config_id=None,
                    name=name,
                    config_path=fname
                )
                cid = configs_repo.upsert_config(config_obj)
                loaded_names.add(name)
                print(f"Loaded config {name} -> id={cid}")
            except Exception as e:
                print(f"Warning: could not load config {fname}: {e}")

        # Remove any configs in DB that are not present on disk
        existing_configs = configs_repo.list_configs()
        existing_names = set(c.name for c in existing_configs)
        to_remove = existing_names - loaded_names
        for name in to_remove:
            configs_repo.delete_config(name)
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
