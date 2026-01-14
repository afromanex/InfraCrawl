from types import SimpleNamespace
from unittest.mock import MagicMock

from infracrawl.services.crawler import Crawler
from infracrawl.domain.http_response import HttpResponse


def make_crawler_with(mocks=None):
    mocks = mocks or {}
    pages_repo = mocks.get("pages_repo", MagicMock())
    links_repo = mocks.get("links_repo", MagicMock())
    http_service = mocks.get("http_service", MagicMock())
    content_review_service = mocks.get("content_review_service", MagicMock())
    robots_service = mocks.get("robots_service", MagicMock())
    link_processor = mocks.get("link_processor", MagicMock())
    return Crawler(pages_repo=pages_repo, links_repo=links_repo,
                   http_service=http_service, content_review_service=content_review_service,
                   robots_service=robots_service, link_processor=link_processor)


def test_fetch_raises_logs_and_returns_none(caplog):
    http = MagicMock()
    http.fetch.side_effect = RuntimeError("network down")
    pages = MagicMock()
    c = make_crawler_with({"http_service": http, "pages_repo": pages})
    context = SimpleNamespace(config=SimpleNamespace(config_id=1))

    caplog.clear()
    body = c._fetch_and_store("http://example.test", context)
    assert body is None
    assert any("Fetch error" in r.message or "Fetch error" in r.getMessage() for r in caplog.records)


def test_storage_failure_logs_and_returns_none(caplog):
    http = MagicMock()
    http.fetch.return_value = HttpResponse(200, "ok")
    pages = MagicMock()
    pages.upsert_page.side_effect = Exception("db write failed")
    c = make_crawler_with({"http_service": http, "pages_repo": pages})
    context = SimpleNamespace(config=SimpleNamespace(config_id=2))

    caplog.clear()
    body = c._fetch_and_store("http://example.test/page", context)
    assert body is None
    assert any("Storage error" in r.message or "Storage error" in r.getMessage() for r in caplog.records)


def test_non_200_status_is_logged_and_body_returned(caplog):
    http = MagicMock()
    http.fetch.return_value = HttpResponse(500, "server error")
    pages = MagicMock()
    pages.upsert_page.return_value = 42
    c = make_crawler_with({"http_service": http, "pages_repo": pages})
    context = SimpleNamespace(config=SimpleNamespace(config_id=3))

    caplog.clear()
    body = c._fetch_and_store("http://example.test/fail", context)
    assert body == "server error"
    assert any("Non-success status" in r.message or "Non-success status" in r.getMessage() for r in caplog.records)
