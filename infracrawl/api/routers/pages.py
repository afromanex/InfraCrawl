from typing import Optional

from fastapi import APIRouter, HTTPException
from infracrawl.services.config_service import ConfigService


def create_pages_router(pages_repo, config_service: ConfigService):
    router = APIRouter(prefix="/pages", tags=["Pages"])

    @router.get("/")
    def list_pages(config: Optional[str] = None, include_page_content: Optional[bool] = None, limit: Optional[int] = 100, offset: Optional[int] = 0):
        config_id = None
        if config:
            cfg = config_service.configs_repo.get_config(config)
            if not cfg:
                raise HTTPException(status_code=404, detail="config not found")
            config_id = cfg.config_id
        pages = pages_repo.fetch_pages(full=include_page_content, limit=limit, offset=offset, config_id=config_id)
        return {"pages": [p.__dict__ for p in pages], "limit": limit, "offset": offset}

    @router.get("/{page_id}")
    def get_page(page_id: int, include_page_content: Optional[bool] = None, full: Optional[bool] = None):
        include = include_page_content if include_page_content is not None else (full if full is not None else False)
        p = pages_repo.get_page_by_id(page_id)
        if not p:
            raise HTTPException(status_code=404, detail="page not found")
        if not include:
            p.page_content = None
        return p.__dict__

    return router
