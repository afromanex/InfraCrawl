from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

from infracrawl.domain.config import CrawlerConfig
from infracrawl.services.config_service import ConfigService


class CrawlRequest(BaseModel):
    url: Optional[str] = None
    config: Optional[str] = None
    depth: Optional[int] = None


def create_app(pages_repo, links_repo, config_service: ConfigService, start_crawl_callback):
    """Return a FastAPI app with control endpoints.

    - `start_crawl_callback(config)` will be scheduled as a background task when a crawl is requested.
    """

    app = FastAPI(title="InfraCrawl Control API")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/export")
    def export(full: bool = False, limit: Optional[int] = None):
        pages = pages_repo.fetch_pages(full=full, limit=limit)
        links = links_repo.fetch_links(limit=limit)
        return {"pages": [p.__dict__ for p in pages], "links": [l.__dict__ for l in links]}

    @app.get("/configs")
    def list_configs():
        configs = config_service.list_configs()
        return [{"config_id": c.config_id, "name": c.name, "config_path": c.config_path, "created_at": c.created_at, "updated_at": c.updated_at} for c in configs]

    @app.get("/pages")
    def list_pages(config: Optional[str] = None, limit: Optional[int] = 100, offset: Optional[int] = 0, full: bool = False):
        config_id = None
        if config:
            cfg = config_service.configs_repo.get_config(config)
            if not cfg:
                raise HTTPException(status_code=404, detail="config not found")
            config_id = cfg.config_id
        pages = pages_repo.fetch_pages(full=full, limit=limit, offset=offset, config_id=config_id)
        return {"pages": [p.__dict__ for p in pages], "limit": limit, "offset": offset}

    @app.get("/pages/{page_id}")
    def get_page(page_id: int, full: bool = False):
        p = pages_repo.get_page_by_id(page_id)
        if not p:
            raise HTTPException(status_code=404, detail="page not found")
        if not full:
            p.page_content = None
        return p.__dict__

    @app.post("/crawl", status_code=202)
    def crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
        if not (req.url or req.config):
            raise HTTPException(status_code=400, detail="missing url or config")

        # Require a config name and use the ConfigService to load the full CrawlerConfig
        if req.config:
            cfg = config_service.get_config(req.config)
            if not cfg:
                raise HTTPException(status_code=404, detail="config not found")
            use_depth = req.depth if req.depth is not None else cfg.max_depth
            if req.depth is not None and cfg is not None:
                cfg = CrawlerConfig(cfg.config_id, cfg.name, cfg.config_path, root_urls=cfg.root_urls, max_depth=use_depth, robots=cfg.robots, refresh_days=cfg.refresh_days)
            background_tasks.add_task(start_crawl_callback, cfg)
            return {"status": "started"}

        # Do not accept direct URLs here — only config names are supported
        raise HTTPException(status_code=400, detail="/crawl only accepts a config name")

    @app.post("/reload")
    def reload(data: dict, background_tasks: BackgroundTasks):
        config_name = data.get("config")
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

    return app
