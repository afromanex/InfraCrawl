from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from infracrawl.api.routers.crawlers import create_crawlers_router


def _get_endpoint(router, path: str, method: str):
    for route in router.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set())
        if method.upper() in methods:
            return route.endpoint
    raise AssertionError(f"No route found for {method} {path}")


def test_export_404_without_leaking_exception():
    """Export endpoint should return 404 without exposing internal exception details."""
    def _boom(name):
        raise RuntimeError("internal database error")
    
    config_service = Mock(get_config=Mock(side_effect=_boom))
    pages_repo = Mock()
    links_repo = Mock()
    crawl_registry = Mock()
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/export", "GET")

    with pytest.raises(HTTPException) as exc:
        endpoint(config="missing", limit=None)
    assert exc.value.status_code == 404
    assert exc.value.detail == "config not found"


def test_crawl_404_without_leaking_exception():
    """Crawl start endpoint should return 404 without exposing internal exception details."""
    def _boom(name):
        raise RuntimeError("internal database error")

    config_service = Mock(get_config=Mock(side_effect=_boom))
    pages_repo = Mock()
    links_repo = Mock()
    crawl_registry = Mock()
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/crawl/{config}/start", "POST")

    with pytest.raises(HTTPException) as exc:
        endpoint(config="missing", background_tasks=Mock())
    assert exc.value.status_code == 404
    assert exc.value.detail == "config not found"


def test_remove_404_without_leaking_exception():
    """Remove endpoint should return 404 without exposing internal exception details."""
    def _boom(name):
        raise RuntimeError("internal database error")

    config_service = Mock(get_config=Mock(side_effect=_boom))
    pages_repo = Mock()
    links_repo = Mock()
    crawl_registry = Mock()
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/remove", "DELETE")

    with pytest.raises(HTTPException) as exc:
        endpoint(config="missing")
    assert exc.value.status_code == 404
    assert exc.value.detail == "config not found"


def test_remove_500_without_leaking_exception():
    """Remove endpoint should return 500 without exposing internal exception details."""
    def _boom(*args, **kwargs):
        raise RuntimeError("disk failure")

    cfg = SimpleNamespace(config_id=123)
    config_service = Mock(get_config=Mock(return_value=cfg))
    pages_repo = Mock(get_page_ids_by_config=Mock(side_effect=_boom))
    links_repo = Mock()
    crawl_registry = Mock()
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/remove", "DELETE")

    with pytest.raises(HTTPException) as exc:
        endpoint(config="test")
    assert exc.value.status_code == 500
    assert exc.value.detail == "error removing data"


def test_list_runs_500_without_leaking_exception():
    """List runs endpoint should return 500 without exposing internal exception details."""
    def _boom(*args, **kwargs):
        raise RuntimeError("database connection lost")

    config_service = Mock()
    pages_repo = Mock()
    links_repo = Mock()
    crawl_registry = Mock()
    crawls_repo = Mock(list_runs=Mock(side_effect=_boom))

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/runs", "GET")

    with pytest.raises(HTTPException) as exc:
        endpoint(limit=20)
    assert exc.value.status_code == 500
    assert exc.value.detail == "could not list runs"
