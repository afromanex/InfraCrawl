import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Optional

from infracrawl import config
from infracrawl.container import Container
from infracrawl.api.server import create_app
import uvicorn
import os


def main(container: Optional[Container] = None):
    """
    Main entry point for the InfraCrawl application.
    
    Args:
        container: Optional Container instance for dependency injection.
                  If None, a new container will be created with default configuration.
    """
    # Create container if not provided (dependency injection)
    if container is None:
        container = Container()
        # Configure with environment variables and defaults
        container.config.database_url.from_value(config.DATABASE_URL)
        container.config.user_agent.from_value(config.USER_AGENT)
        container.config.http_timeout.from_value(10)
        container.config.crawl_delay.from_value(config.CRAWL_DELAY)
        container.config.scheduler_config_watch_interval_seconds.from_value(config.scheduler_config_watch_interval_seconds())
        container.config.recovery_mode.from_value(config.recovery_mode())
        container.config.recovery_within_seconds.from_value(config.recovery_within_seconds())
        container.config.recovery_message.from_value(config.recovery_message())
    
    # Wire dependencies
    container.wire(modules=[__name__])
    
    # Get services from container
    pages_repo = container.pages_repository()
    links_repo = container.links_repository()
    config_service = container.config_service()
    crawler = container.crawler()
    crawl_registry = container.crawl_registry()
    crawls_repo = container.crawls_repository()
    scheduler = container.scheduler_service()
    
    # Load YAML configs and upsert into DB. Remove DB configs not present on disk.
    try:
        config_service.sync_configs_with_disk()
    except Exception as e:
        print(f"Warning: could not load configs: {e}")

    # Start control HTTP server
    port_env = os.getenv("INFRACRAWL_PORT") or os.getenv("PORT")
    try:
        server_port = int(port_env) if port_env else 8000
    except Exception:
        print(f"Warning: Invalid port value '{port_env}', using default 8000")
        server_port = 8000
    
    app = create_app(
        pages_repo,
        links_repo,
        config_service,
        crawler.crawl,
        crawl_registry=crawl_registry,
        scheduler=scheduler,
        crawls_repo=crawls_repo,
    )

    print(f"Control server (FastAPI/uvicorn) listening on 0.0.0.0:{server_port}")
    try:
        uvicorn.run(app, host='0.0.0.0', port=server_port)
    except KeyboardInterrupt:
        print("Shutting down")


if __name__ == '__main__':
    main()
