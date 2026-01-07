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
from infracrawl.api.server import create_server


pages_repo = PagesRepository()
links_repo = LinksRepository()
configs_repo = ConfigsRepository()


# Create a single Crawler instance and expose its `crawl` method as the server callback.
# This keeps dependency injection explicit and allows the server to pass a `CrawlerConfig`
# directly into `crawler.crawl(config)`.



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
    # Instantiate the crawler once and pass its `crawl` method as the callback
    crawler = Crawler(
        pages_repo=pages_repo,
        links_repo=links_repo,
        configs_repo=configs_repo
    )
    server = create_server(pages_repo, links_repo, config_service, crawler.crawl, host='0.0.0.0', port=server_port)

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
