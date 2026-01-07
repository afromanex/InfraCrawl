from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from infracrawl.domain.config import CrawlerConfig
from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry


class CrawlRequest(BaseModel):
    config: str


class ReloadRequest(BaseModel):
    config: str


class RemoveRequest(BaseModel):
    config: str


def create_crawlers_router(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback, crawl_registry: InMemoryCrawlRegistry = None):
    router = APIRouter(prefix="/crawlers", tags=["Crawlers"])

    @router.get("/export")
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
        links = links_repo.fetch_links(limit=limit, config_id=config_id)

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

        return {"pages": [page_to_dict(p) for p in pages], "links": [l.__dict__ for l in links]}

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

        def _run_and_track(cfg, cid=None, stop_event=None):
            try:
                # pass stop_event into the crawl callback so the worker can exit cooperatively
                start_crawl_callback(cfg, stop_event) if stop_event is not None else start_crawl_callback(cfg)
                if cid and crawl_registry is not None:
                    crawl_registry.finish(cid, status="finished")
            except Exception as e:
                if cid and crawl_registry is not None:
                    crawl_registry.finish(cid, status="failed", error=str(e))
                raise

        background_tasks.add_task(_run_and_track, cfg, crawl_id, stop_event)
        return {"status": "started", "crawl_id": crawl_id}

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

    @router.post("/reload")
    def reload(req: ReloadRequest, background_tasks: BackgroundTasks):
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
            raise HTTPException(status_code=500, detail=f"error clearing data: {e}")

        # register reload crawl in registry (if provided)
        crawl_id = None
        if crawl_registry is not None:
            crawl_id = crawl_registry.start(config_name=cfg.config_path, config_id=cfg.config_id)

        def _run_and_track(cfg, cid=None):
            try:
                start_crawl_callback(cfg)
                if cid and crawl_registry is not None:
                    crawl_registry.finish(cid, status="finished")
            except Exception as e:
                if cid and crawl_registry is not None:
                    crawl_registry.finish(cid, status="failed", error=str(e))
                raise

        background_tasks.add_task(_run_and_track, cfg, crawl_id)
        return {"status": "reloading", "deleted_pages": deleted_pages, "deleted_links": deleted_links, "crawl_id": crawl_id}

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

    return router
