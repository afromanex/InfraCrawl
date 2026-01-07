from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from infracrawl.domain.config import CrawlerConfig
from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry


class CrawlRequest(BaseModel):
    config: str
    depth: Optional[int] = None


class ReloadRequest(BaseModel):
    config: str


def create_crawlers_router(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback, crawl_registry: InMemoryCrawlRegistry = None):
    router = APIRouter(prefix="/crawlers", tags=["Crawlers"])

    @router.get("/export")
    def export(config: Optional[str] = None, include_page_content: Optional[bool] = None, full: Optional[bool] = None, limit: Optional[int] = None):
        # include_page_content is the preferred param; full is accepted as a fallback for compatibility
        include = include_page_content if include_page_content is not None else (full if full is not None else False)
        config_id = None
        if config:
            cfg = config_service.get_config(config)
            if not cfg:
                raise HTTPException(status_code=404, detail="config not found")
            config_id = cfg.config_id
        pages = pages_repo.fetch_pages(full=include, limit=limit, config_id=config_id)
        links = links_repo.fetch_links(limit=limit, config_id=config_id)
        return {"pages": [p.__dict__ for p in pages], "links": [l.__dict__ for l in links]}

    @router.post("/crawl", status_code=202)
    def crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
        if not req.config:
            raise HTTPException(status_code=400, detail="missing config")
        cfg = config_service.get_config(req.config)
        if not cfg:
            raise HTTPException(status_code=404, detail="config not found")
        use_depth = req.depth if req.depth is not None else cfg.max_depth
        if req.depth is not None and cfg is not None:
            cfg = CrawlerConfig(cfg.config_id, cfg.name, cfg.config_path, root_urls=cfg.root_urls, max_depth=use_depth, robots=cfg.robots, refresh_days=cfg.refresh_days)
        # register crawl in registry (if provided)
        crawl_id = None
        if crawl_registry is not None:
            crawl_id = crawl_registry.start(config_name=cfg.name, config_id=cfg.config_id)

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
            crawl_id = crawl_registry.start(config_name=cfg.name, config_id=cfg.config_id)

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

    return router
