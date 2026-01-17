from unittest.mock import MagicMock

from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.services.fetcher import HttpServiceFetcher
from infracrawl.services.fetcher_factory import FetcherFactory
from infracrawl.services.configured_crawl_provider import ConfiguredCrawlProviderFactory
from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.http_response import HttpResponse
from infracrawl.domain import CrawlSession


def make_executor_with(mocks=None):
    mocks = mocks or {}
    pages_repo = mocks.get("pages_repo", MagicMock())
    http_service = mocks.get("http_service", MagicMock())
    fetcher = HttpServiceFetcher(http_service)
    fetcher_factory = FetcherFactory(http_fetcher=fetcher, headless_fetcher=fetcher)

    fetch_persist_service = PageFetchPersistService(http_service=http_service, pages_repo=pages_repo)
    crawl_policy = MagicMock()
    link_processor = MagicMock()
    
    provider_factory = ConfiguredCrawlProviderFactory(
        fetcher_factory=fetcher_factory,
        pages_repo=pages_repo,
        crawl_policy=crawl_policy,
        link_processor=link_processor,
        fetch_persist_service=fetch_persist_service,
        delay_seconds=0,
    )

    executor = CrawlExecutor(
        provider_factory=provider_factory,
    )
    return executor, provider_factory


def make_config(config_id: int) -> CrawlerConfig:
    return CrawlerConfig(
        config_id=config_id,
        config_path='p',
        root_urls=['http://example.test'],
        max_depth=0,
        fetch_mode="http",
    )


def test_fetch_raises_logs_and_returns_none(caplog):
    http = MagicMock()
    http.fetch.side_effect = RuntimeError("network down")
    pages = MagicMock()
    executor, provider_factory = make_executor_with({"http_service": http, "pages_repo": pages})
    cfg = make_config(1)
    session = CrawlSession(cfg)
    provider = provider_factory.build(session)
    context = provider.context

    caplog.clear()
    body = provider.fetch_and_store("http://example.test")
    assert body is None
    assert any("Fetch error" in r.message or "Fetch error" in r.getMessage() for r in caplog.records)


def test_storage_failure_logs_and_returns_none(caplog):
    http = MagicMock()
    http.fetch.return_value = HttpResponse(200, "ok")
    pages = MagicMock()
    pages.upsert_page.side_effect = Exception("db write failed")
    executor, provider_factory = make_executor_with({"http_service": http, "pages_repo": pages})
    cfg = make_config(2)
    session = CrawlSession(cfg)
    provider = provider_factory.build(session)
    context = provider.context

    caplog.clear()
    body = provider.fetch_and_store("http://example.test/page")
    assert body is None
    assert any("Storage error" in r.message or "Storage error" in r.getMessage() for r in caplog.records)


def test_non_200_status_is_logged_and_body_returned(caplog):
    http = MagicMock()
    http.fetch.return_value = HttpResponse(500, "server error")
    pages = MagicMock()
    pages.upsert_page.return_value = 42
    executor, provider_factory = make_executor_with({"http_service": http, "pages_repo": pages})
    cfg = make_config(3)
    session = CrawlSession(cfg)
    provider = provider_factory.build(session)
    context = provider.context

    caplog.clear()
    body = provider.fetch_and_store("http://example.test/fail")
    assert body == "server error"
    assert any("Non-success status" in r.message or "Non-success status" in r.getMessage() for r in caplog.records)
