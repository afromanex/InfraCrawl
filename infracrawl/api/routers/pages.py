from typing import Optional

from fastapi import APIRouter, HTTPException
from infracrawl.services.config_service import ConfigService


def create_pages_router(pages_repo, config_service: ConfigService):
    router = APIRouter(prefix="/pages")

    @router.get("/")
    def list_pages(config: Optional[str] = None, limit: Optional[int] = 100, offset: Optional[int] = 0, full: bool = False):
        config_id = None
        if config:
            cfg = config_service.configs_repo.get_config(config)
            if not cfg:
                raise HTTPException(status_code=404, detail="config not found")
            config_id = cfg.config_id
        pages = pages_repo.fetch_pages(full=full, limit=limit, offset=offset, config_id=config_id)
        return {"pages": [p.__dict__ for p in pages], "limit": limit, "offset": offset}

    @router.get("/{page_id}")
    def get_page(page_id: int, full: bool = False):
        p = pages_repo.get_page_by_id(page_id)
        if not p:
            raise HTTPException(status_code=404, detail="page not found")
        if not full:
            p.page_content = None
        return p.__dict__

    return router
