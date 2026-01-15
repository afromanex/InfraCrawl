
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from infracrawl.services.config_service import ConfigService
from infracrawl.api.routers import (
    create_configs_router,
    create_pages_router,
    create_crawlers_router,
    create_systems_router,
)
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry
from infracrawl.services.scheduler_service import SchedulerService
from infracrawl.repository.crawls import CrawlsRepository
from fastapi import Depends
from infracrawl.api.auth import require_admin
from fastapi.staticfiles import StaticFiles


def create_app(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback, crawl_registry: InMemoryCrawlRegistry = None, scheduler: SchedulerService = None):
    """Return a FastAPI app with control endpoints.

    - `start_crawl_callback(config)` will be scheduled as a background task when a crawl is requested.
    - `crawl_registry` (optional): If not provided, creates InMemoryCrawlRegistry.
    - `scheduler` (optional): If not provided, creates SchedulerService.
    """
    # TODO: Optional parameters only used for testing. Simpler: always create defaults here, let tests mock/patch. Reduces parameter count from 6 to 4.

    # Create default registry if not provided (allows dependency injection for testing)
    if crawl_registry is None:
        crawl_registry = InMemoryCrawlRegistry()
    crawls_repo = CrawlsRepository()

    # Create default scheduler if not provided (allows dependency injection for testing)
    if scheduler is None:
        scheduler = SchedulerService(config_service, start_crawl_callback, crawl_registry)

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
    app.include_router(create_pages_router(pages_repo, config_service))
    app.include_router(create_crawlers_router(pages_repo, links_repo, config_service, start_crawl_callback, crawl_registry, crawls_repo), dependencies=[Depends(require_admin)])

    # Serve minimal UI
    app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

    return app
