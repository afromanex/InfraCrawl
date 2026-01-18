from fastapi import APIRouter, HTTPException, Response
from infracrawl.services.config_service import ConfigService


def create_configs_router(config_service: ConfigService):
    router = APIRouter(prefix="/configs", tags=["Configs"])

    @router.get("/")
    def list_configs():
        configs = config_service.list_configs()
        # Load full config from YAML for each config to get schedule and other fields
        result = []
        for c in configs:
            try:
                full_config = config_service.get_config(c.config_path)
                result.append({
                    "config_id": full_config.config_id,
                    "config_path": full_config.config_path,
                    "root_urls": full_config.root_urls,
                    "max_depth": full_config.max_depth,
                    "schedule": full_config.schedule,
                    "resume_on_application_restart": full_config.resume_on_application_restart,
                    "fetch_mode": full_config.fetch_mode,
                    "robots": full_config.robots,
                    "refresh_days": full_config.refresh_days,
                })
            except Exception as e:
                # If we can't load the full config, return metadata only
                result.append({
                    "config_id": c.config_id,
                    "config_path": c.config_path,
                    "root_urls": [],
                    "max_depth": 0,
                    "schedule": None,
                    "resume_on_application_restart": False,
                    "fetch_mode": "http",
                    "robots": True,
                    "refresh_days": None,
                })
        return result

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
