import os
import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class LoginRequest(BaseModel):
    password: str


def create_auth_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/login")
    def login(req: LoginRequest):
        admin = os.getenv("ADMIN_TOKEN")
        if not admin:
            raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
        if not secrets.compare_digest(req.password or "", admin):
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {"access_token": admin}

    return router
