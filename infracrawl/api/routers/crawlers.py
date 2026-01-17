import json
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from starlette.responses import StreamingResponse

from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry
from infracrawl.repository.crawls import CrawlsRepository
from infracrawl.services.scheduled_crawl_job_runner import ScheduledCrawlJobRunner


def create_crawlers_router(
    pages_repo,
    links_repo,
    config_service: ConfigService,
    session_factory,
    start_crawl_callback,
    crawl_registry: Optional[InMemoryCrawlRegistry],
    crawls_repo: CrawlsRepository,
) -> APIRouter:
    router = APIRouter(prefix="/crawlers", tags=["Crawlers"])

    job_runner = ScheduledCrawlJobRunner(
        config_provider=config_service,
        session_factory=session_factory,
        start_crawl_callback=start_crawl_callback,
        crawls_repo=crawls_repo,
    )

    @router.get(
        "/export",
        responses={
            200: {
                "content": {
                    "application/x-ndjson": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
                "description": "NDJSON stream (one JSON object per line)",
            }
        },
    )
    def export(config: Optional[str] = None, limit: Optional[int] = None):
        config_id = None
        if config:
            try:
                cfg = config_service.get_config(config)
            except Exception:
                raise HTTPException(status_code=404, detail="config not found")
            config_id = cfg.config_id

        pages = pages_repo.fetch_pages(full=True, limit=limit, config_id=config_id)

        def gen_ndjson():
            for p in pages:
                yield (json.dumps(p.__dict__, default=str) + "\n").encode("utf-8")

        return StreamingResponse(gen_ndjson(), media_type="application/x-ndjson")

    @router.post("/crawl/{config}/start", status_code=202)
    def crawl(config: str, background_tasks: BackgroundTasks):
        if not config:
            raise HTTPException(status_code=400, detail="missing config")
        try:
            cfg = config_service.get_config(config)
        except Exception:
            raise HTTPException(status_code=404, detail="config not found")

        # Validate config synchronously, but run the crawl + tracking in the background.
        background_tasks.add_task(job_runner.run_config, cfg)
        return {"status": "started"}

    @router.get("/active")
    def list_active_crawls():
        if crawl_registry is None:
            return {"active": []}
        return {"active": crawl_registry.list_active()}

    @router.get("/active/{crawl_id}")
    def get_crawl(crawl_id: str):
        if crawl_registry is None:
            raise HTTPException(status_code=404, detail="no registry configured")
        rec = crawl_registry.get(crawl_id)
        if not rec:
            raise HTTPException(status_code=404, detail="crawl not found")
        return rec

    @router.post("/cancel/{crawl_id}")
    def cancel_crawl(crawl_id: str):
        if crawl_registry is None:
            raise HTTPException(status_code=404, detail="no registry configured")
        ok = crawl_registry.cancel(crawl_id)
        if not ok:
            raise HTTPException(status_code=404, detail="crawl not found or cannot cancel")
        return {"status": "cancelling", "crawl_id": crawl_id}

    @router.delete("/remove")
    def remove(config: str):
        config_name = config
        if not config_name:
            raise HTTPException(status_code=400, detail="missing config")

        try:
            cfg = config_service.get_config(config_name)
        except Exception:
            raise HTTPException(status_code=404, detail="config not found")

        try:
            page_ids = pages_repo.get_page_ids_by_config(cfg.config_id)
            deleted_links = 0
            deleted_pages = 0
            if page_ids:
                deleted_links = links_repo.delete_links_for_page_ids(page_ids)
                deleted_pages = pages_repo.delete_pages_by_ids(page_ids)
        except Exception:
            raise HTTPException(status_code=500, detail="error removing data")

        return {
            "status": "removed",
            "deleted_pages": deleted_pages,
            "deleted_links": deleted_links,
        }

    @router.get("/runs")
    def list_runs(limit: Optional[int] = 20):
        """Return the last `limit` crawl runs (most recent first)."""
        try:
            runs = crawls_repo.list_runs(limit=limit)
        except Exception:
            raise HTTPException(status_code=500, detail="could not list runs")

        def r_to_dict(r):
            return {
                "run_id": r.run_id,
                "config_id": r.config_id,
                "config_path": r.config_path,
                "start_timestamp": r.start_timestamp,
                "end_timestamp": r.end_timestamp,
                "exception": r.exception,
            }

        return [r_to_dict(r) for r in runs]

    @router.get("/stats/{config}")
    def get_config_stats(config: str):
        """Get statistics (page and link counts) for a config."""
        if not config:
            raise HTTPException(status_code=400, detail="missing config")
        try:
            cfg = config_service.get_config(config)
        except Exception:
            raise HTTPException(status_code=404, detail="config not found")

        try:
            # Only count pages that have been fetched (have content)
            page_ids = pages_repo.get_fetched_page_ids_by_config(cfg.config_id)
            page_count = len(page_ids) if page_ids else 0
            link_count = 0
            if page_ids:
                link_count = links_repo.count_links_for_page_ids(page_ids)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"error getting stats: {str(e)}")

        return {
            "config_path": config,
            "pages": page_count,
            "links": link_count,
        }

    return router
