import os
from fastapi import HTTPException
import pytest

from infracrawl.api.routers.auth import create_auth_router, LoginRequest


def _get_endpoint(router, path: str, method: str):
    for route in router.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set())
        if method.upper() in methods:
            return route.endpoint
    raise AssertionError(f"No route found for {method} {path}")


def test_login_503_when_admin_token_missing(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    router = create_auth_router()
    endpoint = _get_endpoint(router, "/auth/login", "POST")

    with pytest.raises(HTTPException) as exc:
        endpoint(LoginRequest(password="any"))
    assert exc.value.status_code == 503
    assert exc.value.detail == "ADMIN_TOKEN not configured"


def test_login_401_on_wrong_password(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    router = create_auth_router()
    endpoint = _get_endpoint(router, "/auth/login", "POST")

    with pytest.raises(HTTPException) as exc:
        endpoint(LoginRequest(password="wrong"))
    assert exc.value.status_code == 401
    assert exc.value.detail == "Unauthorized"


def test_login_success_returns_token(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret")
    router = create_auth_router()
    endpoint = _get_endpoint(router, "/auth/login", "POST")

    resp = endpoint(LoginRequest(password="secret"))
    assert resp == {"access_token": "secret"}