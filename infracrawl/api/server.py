
from fastapi import FastAPI

from infracrawl.services.config_service import ConfigService
from infracrawl.api.routers.configs import create_configs_router
from infracrawl.api.routers.pages import create_pages_router
from infracrawl.api.routers.crawlers import create_crawlers_router
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry
from infracrawl.services.scheduler_service import SchedulerService
from fastapi import Depends
from infracrawl.api.auth import require_admin


def create_app(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback):
    """Return a FastAPI app with control endpoints.

    - `start_crawl_callback(config)` will be scheduled as a background task when a crawl is requested.
    """

    app = FastAPI(title="InfraCrawl Control API")

    # include routers from separate modules
    from infracrawl.api.routers.systems import create_systems_router

    app.include_router(create_systems_router())
    # Protect configuration and crawler control endpoints with admin token.
    app.include_router(create_configs_router(config_service), dependencies=[Depends(require_admin)])
    app.include_router(create_pages_router(pages_repo, config_service))
    # create an in-memory crawl registry and pass into the crawlers router
    crawl_registry = InMemoryCrawlRegistry()
    app.include_router(create_crawlers_router(pages_repo, links_repo, config_service, start_crawl_callback, crawl_registry), dependencies=[Depends(require_admin)])

    # Scheduler: schedule jobs declared inside YAML configs via `schedule` key.
    scheduler = SchedulerService(config_service, start_crawl_callback, crawl_registry)

    @app.on_event("startup")
    def _start_scheduler():
        try:
            scheduler.start()
        except Exception:
            # Non-fatal: scheduler failure should not prevent API from running
            import logging

            logging.exception("Failed to start scheduler")

    @app.on_event("shutdown")
    def _shutdown_scheduler():
        try:
            scheduler.shutdown()
        except Exception:
            import logging

            logging.exception("Failed to shut down scheduler")

    return app
