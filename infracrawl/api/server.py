from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from infracrawl.container import Container
from infracrawl.api.routers import (
    create_configs_router,
    create_crawlers_router,
    create_systems_router,
)
from fastapi import Depends
from infracrawl.api.auth import require_admin
from fastapi.staticfiles import StaticFiles


def create_app(container: Container) -> FastAPI:
    """Return a FastAPI app with control endpoints.

    This app is wired exclusively via the DI container (single composition root).
    """

    pages_repo = container.pages_repository()
    links_repo = container.links_repository()
    config_service = container.config_service()
    crawl_executor = container.crawl_executor()
    crawl_registry = container.crawl_registry()
    crawls_repo = container.crawls_repository()
    scheduler = container.scheduler_service()

    start_crawl_callback = crawl_executor.crawl

    @asynccontextmanager
    async def _lifespan(app):
        try:
            scheduler.start()
        except Exception:
            logging.exception("Failed to start scheduler")
        try:
            yield
        finally:
            try:
                scheduler.shutdown()
            except Exception:
                logging.exception("Failed to shut down scheduler")

    app = FastAPI(title="InfraCrawl Control API", lifespan=_lifespan)

    app.include_router(create_systems_router())
    # Protect configuration and crawler control endpoints with admin token.
    app.include_router(create_configs_router(config_service), dependencies=[Depends(require_admin)])
    app.include_router(create_crawlers_router(pages_repo, links_repo, config_service, start_crawl_callback, crawl_registry, crawls_repo), dependencies=[Depends(require_admin)])

    # Serve minimal UI
    app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

    return app
