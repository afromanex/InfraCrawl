import pytest
from unittest.mock import MagicMock
from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.services.link_processor import LinkProcessor
from infracrawl.services.link_persister import LinkPersister
from infracrawl.services.configured_crawl_provider import ConfiguredCrawlProviderFactory
from types import SimpleNamespace

from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.crawl_session import CrawlSession
from infracrawl.domain.http_response import HttpResponse


@pytest.fixture
def executor_with_mocks():
    pages_repo = MagicMock()
    links_repo = MagicMock()
    fetcher = MagicMock()
    fetcher_factory = MagicMock()
    fetcher_factory.get.return_value = fetcher

    content_review_service = MagicMock()
    link_persister = LinkPersister(pages_repo, links_repo)
    link_processor = LinkProcessor(content_review_service, link_persister)

    crawl_policy = MagicMock()
    crawl_policy.should_skip_due_to_depth.return_value = False
    crawl_policy.should_skip_due_to_robots.return_value = False
    crawl_policy.should_skip_due_to_refresh.return_value = False

    fetch_persist_service = MagicMock()
    fetch_persist_service.extract_and_persist.return_value = type("Page", (), {"page_id": 1})()

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
    return executor, pages_repo, links_repo, fetcher, provider_factory, content_review_service, crawl_policy


def test_crawl_respects_max_depth(executor_with_mocks):
    executor, pages_repo, links_repo, fetcher, provider_factory, content_review_service, crawl_policy = executor_with_mocks
    # Setup: ensure_page returns a fake id
    pages_repo.ensure_page.return_value = 1
    # Patch fetch to return dummy html
    fetcher.fetch = MagicMock(return_value=HttpResponse(200, '<html></html>'))
    content_review_service.extract_links = MagicMock(return_value=[])
    # Should only call ensure_page once for depth=0
    cfg = CrawlerConfig(config_id=None, config_path='p', root_urls=['http://example.com'], max_depth=0, fetch_mode="http")
    session = CrawlSession(cfg)
    executor.crawl(session)
    assert pages_repo.ensure_page.call_count == 1
    assert fetcher.fetch.call_count == 1


def test_crawl_skips_robots(executor_with_mocks):
    executor, pages_repo, links_repo, fetcher, provider_factory, content_review_service, crawl_policy = executor_with_mocks
    pages_repo.ensure_page.return_value = 1
    # Mock the policy's robots check
    crawl_policy.should_skip_due_to_robots = MagicMock(return_value=True)
    fetcher.fetch = MagicMock()
    content_review_service.extract_links = MagicMock()
    cfg = CrawlerConfig(config_id=None, config_path='p', root_urls=['http://example.com'], max_depth=1, fetch_mode="http")
    session = CrawlSession(cfg)
    executor.crawl(session)
    # Should not fetch if robots disallowed
    assert not fetcher.fetch.called


def test_crawl_refresh_days_skips_recent(executor_with_mocks):
    executor, pages_repo, links_repo, fetcher, provider_factory, content_review_service, crawl_policy = executor_with_mocks
    pages_repo.ensure_page.return_value = 1
    crawl_policy.should_skip_due_to_refresh = MagicMock(return_value=True)
    fetcher.fetch = MagicMock()
    content_review_service.extract_links = MagicMock()
    # Simulate config with refresh_days=10
    cfg = CrawlerConfig(config_id=123, config_path='p', root_urls=['http://example.com'], max_depth=1, robots=True, refresh_days=10, fetch_mode="http")
    session = CrawlSession(cfg)
    executor.crawl(session)
    # Should not fetch if fetched less than refresh_days ago
    assert not fetcher.fetch.called


def test_crawl_inserts_links(executor_with_mocks):
    executor, pages_repo, links_repo, fetcher, provider_factory, content_review_service, crawl_policy = executor_with_mocks
    # Mock batch method to return URL -> ID mapping
    pages_repo.ensure_pages_batch.return_value = {'http://example.com/next': 1}
    fetcher.fetch = MagicMock(return_value=HttpResponse(200, '<html></html>'))
    content_review_service.extract_links = MagicMock(return_value=[('http://example.com/next', 'next')])
    links_repo.insert_links_batch = MagicMock()
    # Patch _same_host to always True on the link_processor that the provider will use
    provider_factory.link_processor._same_host = MagicMock(return_value=True)
    cfg = CrawlerConfig(config_id=None, config_path='p', root_urls=['http://example.com'], max_depth=1, fetch_mode="http")
    session = CrawlSession(cfg)
    executor.crawl(session)
    # Should insert links via batch method
    assert links_repo.insert_links_batch.called
