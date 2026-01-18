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


def test_get_crawl_log_happy_path():
    pages_repo = Mock(get_recent_fetched_urls_by_config=Mock(return_value=["u10", "u9", "u8"]))
    links_repo = Mock()
    config_service = Mock()
    crawl_registry = Mock(get=Mock(return_value={"config_id": 42}))
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/active/{crawl_id}/log", "GET")

    result = endpoint(crawl_id="abc")
    assert result == {"crawl_id": "abc", "recent_urls": ["u10", "u9", "u8"]}


def test_get_crawl_log_404_when_missing_or_no_registry():
    pages_repo = Mock()
    links_repo = Mock()
    config_service = Mock()
    crawls_repo = Mock()

    # No registry configured
    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), None, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/active/{crawl_id}/log", "GET")

    with pytest.raises(HTTPException) as exc:
        endpoint(crawl_id="abc")
    assert exc.value.status_code == 404
    assert exc.value.detail == "no registry configured"

    # Registry returns None for missing crawl
    crawl_registry = Mock(get=Mock(return_value=None))
    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/active/{crawl_id}/log", "GET")

    with pytest.raises(HTTPException) as exc:
        endpoint(crawl_id="missing")
    assert exc.value.status_code == 404
    assert exc.value.detail == "crawl not found"


def test_get_config_log_happy_path():
    pages_repo = Mock(get_recent_fetched_urls_by_config=Mock(return_value=["x3", "x2", "x1"]))
    links_repo = Mock()
    cfg = SimpleNamespace(config_id=7)
    config_service = Mock(get_config=Mock(return_value=cfg))
    crawl_registry = Mock()
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/log/{config}", "GET")

    result = endpoint(config="my.yml")
    assert result == {"config": "my.yml", "recent_urls": ["x3", "x2", "x1"]}


def test_get_config_log_prefers_active_registry_recent_urls():
    pages_repo = Mock(get_recent_fetched_urls_by_config=Mock(return_value=["db3", "db2"]))
    links_repo = Mock()
    config_service = Mock(get_config=Mock(return_value=SimpleNamespace(config_id=7)))
    crawl_registry = Mock(
        list_active=Mock(return_value=[{"id": "abc", "config_name": "my.yml"}]),
        get_recent_urls=Mock(return_value=["mem2", "mem1"]),
    )
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/log/{config}", "GET")

    result = endpoint(config="my.yml")
    # Should return in-memory recent URLs, not DB
    assert result == {"config": "my.yml", "recent_urls": ["mem2", "mem1"]}


def test_get_config_log_errors():
    pages_repo = Mock(get_recent_fetched_urls_by_config=Mock(side_effect=RuntimeError("db error")))
    links_repo = Mock()
    config_service = Mock(get_config=Mock(side_effect=RuntimeError("missing")))
    crawl_registry = Mock()
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/log/{config}", "GET")

    with pytest.raises(HTTPException) as exc:
        endpoint(config="bad.yml")
    assert exc.value.status_code == 404
    assert exc.value.detail == "config not found"

    # Now config resolves but repository errors
    config_service = Mock(get_config=Mock(return_value=SimpleNamespace(config_id=1)))
    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/log/{config}", "GET")
    with pytest.raises(HTTPException) as exc:
        endpoint(config="ok.yml")
    assert exc.value.status_code == 500
    assert exc.value.detail == "could not load crawl log"


def test_get_crawl_log_returns_empty_if_no_config_id():
    pages_repo = Mock()
    links_repo = Mock()
    config_service = Mock()
    crawl_registry = Mock(get=Mock(return_value={"config_id": None}))
    crawls_repo = Mock()

    router = create_crawlers_router(
        pages_repo, links_repo, config_service, Mock(), Mock(), crawl_registry, crawls_repo
    )
    endpoint = _get_endpoint(router, "/crawlers/active/{crawl_id}/log", "GET")

    result = endpoint(crawl_id="abc")
    assert result == {"crawl_id": "abc", "recent_urls": []}
