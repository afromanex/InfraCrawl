from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from infracrawl.api.routers.configs import create_configs_router
from infracrawl.domain.config import CrawlerConfig


def _get_endpoint(router, path: str, method: str):
    for route in router.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set())
        if method.upper() in methods:
            return route.endpoint
    raise AssertionError(f"No route found for {method} {path}")


def test_list_configs_returns_dicts():
    cfg = SimpleNamespace(config_id=1, config_path="configs/x.yml")
    config_service = Mock(list_configs=Mock(return_value=[cfg]))

    router = create_configs_router(config_service)
    endpoint = _get_endpoint(router, "/configs/", "GET")

    assert endpoint() == [{"config_id": 1, "config_path": "configs/x.yml"}]


def test_list_configs_flattens_crawler_config():
    cfg = CrawlerConfig(
        config_id=2,
        config_path="configs/y.yml",
        root_urls=["https://example.org"],
        max_depth=1,
        robots=True,
        refresh_days=7,
        fetch_mode="http",
    )
    config_service = Mock(list_configs=Mock(return_value=[cfg]))

    router = create_configs_router(config_service)
    endpoint = _get_endpoint(router, "/configs/", "GET")

    assert endpoint() == [{"config_id": 2, "config_path": "configs/y.yml"}]


def test_get_config_returns_yaml_response():
    config_service = Mock(get_config_yaml=Mock(return_value="root_urls: []\n"))

    router = create_configs_router(config_service)
    endpoint = _get_endpoint(router, "/configs/{name}", "GET")

    resp = endpoint("test")
    assert resp.media_type == "text/yaml"
    assert resp.body == b"root_urls: []\n"


def test_get_config_404_when_missing():
    config_service = Mock(get_config_yaml=Mock(return_value=None))
    router = create_configs_router(config_service)
    endpoint = _get_endpoint(router, "/configs/{name}", "GET")

    with pytest.raises(HTTPException) as exc:
        endpoint("missing")
    assert exc.value.status_code == 404
    assert exc.value.detail == "config not found"


def test_sync_configs_ok():
    config_service = Mock(sync_configs_with_disk=Mock())
    router = create_configs_router(config_service)
    endpoint = _get_endpoint(router, "/configs/sync", "POST")

    assert endpoint() == {"status": "synced"}


def test_sync_configs_returns_500_without_leaking_exception_details():
    def _boom() -> None:
        raise RuntimeError("db down")

    config_service = Mock(sync_configs_with_disk=Mock(side_effect=_boom))
    router = create_configs_router(config_service)
    endpoint = _get_endpoint(router, "/configs/sync", "POST")

    with pytest.raises(HTTPException) as exc:
        endpoint()
    assert exc.value.status_code == 500
    assert exc.value.detail == "sync failed"
