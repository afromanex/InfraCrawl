from fastapi import APIRouter, HTTPException, Response
from infracrawl.services.config_service import ConfigService


def create_configs_router(config_service: ConfigService):
    router = APIRouter(prefix="/configs", tags=["Configs"])

    @router.get("/")
    def list_configs():
        configs = config_service.list_configs()
        return [c.__dict__ for c in configs]

    @router.get("/{name}")
    def get_config(name: str):
        yaml_content = config_service.get_config_yaml(name)
        if not yaml_content:
            raise HTTPException(status_code=404, detail="config not found")
        return Response(content=yaml_content, media_type="text/yaml")

    @router.post('/sync')
    def sync_configs():
        try:
            config_service.sync_configs_with_disk()
            return {"status": "synced"}
        except Exception:
            raise HTTPException(status_code=500, detail="sync failed")

    return router
