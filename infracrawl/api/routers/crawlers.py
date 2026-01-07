from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from infracrawl.domain.config import CrawlerConfig
from infracrawl.services.config_service import ConfigService


class CrawlRequest(BaseModel):
    config: str
    depth: Optional[int] = None


class ReloadRequest(BaseModel):
    config: str


def create_crawlers_router(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback):
    router = APIRouter(prefix="/crawlers")

    @router.get("/export")
    def export(full: bool = False, limit: Optional[int] = None):
        pages = pages_repo.fetch_pages(full=full, limit=limit)
        links = links_repo.fetch_links(limit=limit)
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
        background_tasks.add_task(start_crawl_callback, cfg)
        return {"status": "started"}

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

        background_tasks.add_task(start_crawl_callback, cfg)
        return {"status": "reloading", "deleted_pages": deleted_pages, "deleted_links": deleted_links}

    return router
