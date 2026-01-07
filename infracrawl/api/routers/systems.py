from fastapi import APIRouter


def create_systems_router():
    router = APIRouter(prefix="/systems", tags=["System"])

    @router.get("/health")
    def health():
        return {"status": "ok"}

    return router
