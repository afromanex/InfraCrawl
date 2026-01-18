from fastapi import APIRouter


def create_systems_router(container_env: dict):
    """Create systems router with access to container environment config."""
    router = APIRouter(prefix="/systems", tags=["System"])

    @router.get("/health")
    def health():
        return {"status": "ok"}

    @router.get("/config")
    def get_config():
        """Return current environment configuration values."""
        return {
            "environment": {
                key: str(value) if value is not None else None
                for key, value in container_env.items()
            }
        }

    return router
