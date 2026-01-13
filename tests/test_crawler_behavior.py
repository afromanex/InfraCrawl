import pytest
from unittest.mock import MagicMock
from infracrawl.services.crawler import Crawler
from infracrawl.domain.config import CrawlerConfig


@pytest.fixture
def crawler_with_mocks():
    pages_repo = MagicMock()
    links_repo = MagicMock()
    return Crawler(
        pages_repo=pages_repo,
        links_repo=links_repo,
        delay=0,
        user_agent='TestAgent/1.0'
    ), pages_repo, links_repo


def test_crawl_respects_max_depth(crawler_with_mocks):
    crawler, pages_repo, links_repo = crawler_with_mocks
    # Setup: ensure_page returns a fake id
    pages_repo.ensure_page.return_value = 1
    # Patch fetch to return dummy html
    crawler.fetch = MagicMock(return_value=(200, '<html></html>'))
    crawler.extract_links = MagicMock(return_value=[])
    # Should only call ensure_page once for depth=0
    cfg = CrawlerConfig(config_id=None, config_path='p', root_urls=['http://example.com'], max_depth=0)
    crawler.crawl(cfg)
    assert pages_repo.ensure_page.call_count == 1
    assert crawler.fetch.call_count == 1


def test_crawl_skips_robots(crawler_with_mocks):
    crawler, pages_repo, links_repo = crawler_with_mocks
    pages_repo.ensure_page.return_value = 1
    crawler._allowed_by_robots = MagicMock(return_value=False)
    crawler.fetch = MagicMock()
    crawler.extract_links = MagicMock()
    cfg = CrawlerConfig(config_id=None, config_path='p', root_urls=['http://example.com'], max_depth=1)
    crawler.crawl(cfg)
    # Should not fetch if robots disallowed
    assert not crawler.fetch.called


def test_crawl_refresh_days_skips_recent(crawler_with_mocks):
    crawler, pages_repo, links_repo = crawler_with_mocks
    pages_repo.ensure_page.return_value = 1
    crawler._allowed_by_robots = MagicMock(return_value=True)
    crawler.fetch = MagicMock()
    crawler.extract_links = MagicMock()
    # Simulate config with refresh_days=10
    cfg = CrawlerConfig(config_id=123, config_path='p', root_urls=['http://example.com'], max_depth=1, robots=True, refresh_days=10)
    # Simulate page fetched 1 day ago
    from datetime import datetime, timedelta
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    pages_repo.get_page_by_url.return_value = type('page', (), {'fetched_at': yesterday})
    crawler.crawl(cfg)
    # Should not fetch if fetched less than refresh_days ago
    assert not crawler.fetch.called


def test_crawl_inserts_links(crawler_with_mocks):
    crawler, pages_repo, links_repo = crawler_with_mocks
    # Always return a valid page id for any call
    pages_repo.ensure_page.return_value = 1
    crawler._allowed_by_robots = MagicMock(return_value=True)
    crawler.fetch = MagicMock(return_value=(200, '<html></html>'))
    crawler.extract_links = MagicMock(return_value=[('http://example.com/next', 'next')])
    links_repo.insert_link = MagicMock()
    # Patch _same_host to always True
    crawler._same_host = MagicMock(return_value=True)
    pages_repo.upsert_page.return_value = 1
    cfg = CrawlerConfig(config_id=None, config_path='p', root_urls=['http://example.com'], max_depth=1)
    crawler.crawl(cfg)
    # Should insert a link
    assert links_repo.insert_link.called
