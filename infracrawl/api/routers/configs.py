from fastapi import APIRouter, HTTPException
from infracrawl.services.config_service import ConfigService


def create_configs_router(config_service: ConfigService):
    router = APIRouter(prefix="/configs")

    @router.get("/")
    def list_configs():
        configs = config_service.list_configs()
        return [{"config_id": c.config_id, "name": c.name, "config_path": c.config_path, "created_at": c.created_at, "updated_at": c.updated_at} for c in configs]

    @router.get("/{name}")
    def get_config(name: str):
        cfg = config_service.get_config(name)
        if not cfg:
            raise HTTPException(status_code=404, detail="config not found")
        return {
            "config_id": cfg.config_id,
            "name": cfg.name,
            "config_path": cfg.config_path,
            "root_urls": cfg.root_urls,
            "max_depth": cfg.max_depth,
            "robots": cfg.robots,
            "refresh_days": cfg.refresh_days,
            "created_at": cfg.created_at,
            "updated_at": cfg.updated_at,
        }

    return router
