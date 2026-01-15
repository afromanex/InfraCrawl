import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Optional

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
    
    # Wire dependencies
    container.wire(modules=[__name__])
    
    # Get services from container
    pages_repo = container.pages_repository()
    links_repo = container.links_repository()
    config_service = container.config_service()
    crawl_executor = container.crawl_executor()
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
        crawl_executor.crawl,
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
