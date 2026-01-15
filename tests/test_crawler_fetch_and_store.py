from types import SimpleNamespace
from unittest.mock import MagicMock

from infracrawl.services.crawler import Crawler
from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.services.fetcher import HttpServiceFetcher
from infracrawl.services.fetcher_factory import FetcherFactory
from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.domain.http_response import HttpResponse


def make_crawler_with(mocks=None):
    mocks = mocks or {}
    pages_repo = mocks.get("pages_repo", MagicMock())
    links_repo = mocks.get("links_repo", MagicMock())
    http_service = mocks.get("http_service", MagicMock())
    fetcher = HttpServiceFetcher(http_service)
    fetcher_factory = FetcherFactory(http_fetcher=fetcher, headless_fetcher=fetcher)

    fetch_persist_service = PageFetchPersistService(http_service=http_service, pages_repo=pages_repo)
    executor = CrawlExecutor(
        pages_repo=pages_repo,
        crawl_policy=MagicMock(),
        link_processor=MagicMock(),
        fetch_persist_service=fetch_persist_service,
        delay_seconds=0,
        fetcher_factory=fetcher_factory,
        extract_links_fn=MagicMock(),
    )
    return Crawler(executor=executor)


def test_fetch_raises_logs_and_returns_none(caplog):
    http = MagicMock()
    http.fetch.side_effect = RuntimeError("network down")
    pages = MagicMock()
    c = make_crawler_with({"http_service": http, "pages_repo": pages})
    context = SimpleNamespace(config=SimpleNamespace(config_id=1, fetch_mode="http"))

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
    context = SimpleNamespace(config=SimpleNamespace(config_id=2, fetch_mode="http"))

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
    context = SimpleNamespace(config=SimpleNamespace(config_id=3, fetch_mode="http"))

    caplog.clear()
    body = c._fetch_and_store("http://example.test/fail", context)
    assert body == "server error"
    assert any("Non-success status" in r.message or "Non-success status" in r.getMessage() for r in caplog.records)
