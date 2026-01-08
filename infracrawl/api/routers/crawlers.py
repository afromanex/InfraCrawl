from typing import Optional
import json

from fastapi import APIRouter, HTTPException, BackgroundTasks
from starlette.responses import StreamingResponse
from pydantic import BaseModel

from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry
from infracrawl.repository.crawls import CrawlsRepository


class CrawlRequest(BaseModel):
    config: str


class ReloadRequest(BaseModel):
    config: str


class RemoveRequest(BaseModel):
    config: str


class ClearRunsRequest(BaseModel):
    config: str
    within_seconds: Optional[int] = None
    message: Optional[str] = None


def create_crawlers_router(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback, crawl_registry: InMemoryCrawlRegistry = None):
    router = APIRouter(prefix="/crawlers", tags=["Crawlers"])
    crawls_repo = CrawlsRepository()

    @router.get(
        "/export",
        responses={
            200: {
                "content": {
                    "application/x-ndjson": {
                        "schema": {"type": "string", "format": "binary"}
                    }
                },
                "description": "NDJSON stream (one JSON object per line)"
            }
        },
    )
    def export(config: Optional[str] = None, include_html: Optional[bool] = None, include_plain_text: Optional[bool] = None, limit: Optional[int] = None):
        # `include_html` and `include_plain_text` control which fields are returned.
        include_html = bool(include_html)
        include_plain_text = bool(include_plain_text)
        config_id = None
        if config:
            cfg = config_service.get_config(config)
            if not cfg:
                raise HTTPException(status_code=404, detail="config not found")
            config_id = cfg.config_id
        # fetch full rows if either HTML or plain text is requested
        fetch_full = include_html or include_plain_text
        pages = pages_repo.fetch_pages(full=fetch_full, limit=limit, config_id=config_id)

        def page_to_dict(p):
            d = {
                "page_id": p.page_id,
                "page_url": p.page_url,
                "http_status": p.http_status,
                "fetched_at": p.fetched_at,
                "config_id": p.config_id,
            }
            if include_html:
                d["page_content"] = p.page_content
            if include_plain_text:
                d["plain_text"] = p.plain_text
            return d

        def gen_ndjson():
            for p in pages:
                yield (json.dumps(page_to_dict(p), default=str) + "\n").encode("utf-8")

        return StreamingResponse(gen_ndjson(), media_type="application/x-ndjson")

    @router.post("/crawl", status_code=202)
    def crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
        if not req.config:
            raise HTTPException(status_code=400, detail="missing config")
        cfg = config_service.get_config(req.config)
        if not cfg:
            raise HTTPException(status_code=404, detail="config not found")
        # depth is taken from the stored config file; do not accept depth from request
        # register crawl in registry (if provided)
        crawl_id = None
        if crawl_registry is not None:
            crawl_id = crawl_registry.start(config_name=cfg.config_path, config_id=cfg.config_id)

        stop_event = crawl_registry.get_stop_event(crawl_id) if crawl_registry is not None else None

        # create DB run record
        run_id = None
        try:
            run_id = crawls_repo.create_run(cfg.config_id)
        except Exception:
            # non-fatal: continue but log server-side
            import logging

            logging.exception("Could not create crawl run record")

        def _run_and_track(cfg, cid=None, stop_event=None, run_id=None):
            try:
                # pass stop_event into the crawl callback so the worker can exit cooperatively
                start_crawl_callback(cfg, stop_event) if stop_event is not None else start_crawl_callback(cfg)
                if cid and crawl_registry is not None:
                    crawl_registry.finish(cid, status="finished")
                if run_id is not None:
                    try:
                        crawls_repo.finish_run(run_id)
                    except Exception:
                        import logging

                        logging.exception("Could not finish crawl run record")
            except Exception as e:
                if cid and crawl_registry is not None:
                    crawl_registry.finish(cid, status="failed", error=str(e))
                if run_id is not None:
                    try:
                        crawls_repo.finish_run(run_id, exception=str(e))
                    except Exception:
                        import logging

                        logging.exception("Could not finish crawl run record (failed)")
                raise

        background_tasks.add_task(_run_and_track, cfg, crawl_id, stop_event, run_id)
        return {"status": "started", "crawl_id": crawl_id, "run_id": run_id}

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
    def remove(req: RemoveRequest):
        config_name = req.config
        if not config_name:
            raise HTTPException(status_code=400, detail="missing config")

        cfg = config_service.get_config(config_name)
        if not cfg:
            raise HTTPException(status_code=404, detail="config not found")

        try:
            page_ids = pages_repo.get_page_ids_by_config(cfg.config_id)
            deleted_links = 0
            deleted_pages = 0
            if page_ids:
                deleted_links = links_repo.delete_links_for_page_ids(page_ids)
                deleted_pages = pages_repo.delete_pages_by_ids(page_ids)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"error removing data: {e}")

        return {"status": "removed", "deleted_pages": deleted_pages, "deleted_links": deleted_links}

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

    @router.post("/runs/clear")
    def clear_runs(req: ClearRunsRequest):
        """Mark recent incomplete runs for a config as finished.

        Useful to clear stale incomplete runs before attempting resume logic.
        """
        config_name = req.config
        if not config_name:
            raise HTTPException(status_code=400, detail="missing config")
        cfg = config_service.get_config(config_name)
        if not cfg:
            raise HTTPException(status_code=404, detail="config not found")

        try:
            cnt = crawls_repo.clear_incomplete_runs(cfg.config_id, within_seconds=req.within_seconds, message=req.message)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"could not clear runs: {e}")

        return {"status": "cleared", "count": cnt}

    return router
