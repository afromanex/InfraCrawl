from datetime import datetime, timedelta
from unittest.mock import MagicMock
from infracrawl.services.crawl_policy import CrawlPolicy
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.config import CrawlerConfig


def test_should_skip_due_to_depth_returns_true_when_negative():
    pages_repo = MagicMock()
    policy = CrawlPolicy(pages_repo)
    assert policy.should_skip_due_to_depth(-1)


def test_should_skip_due_to_depth_returns_false_when_zero_or_positive():
    pages_repo = MagicMock()
    policy = CrawlPolicy(pages_repo)
    assert not policy.should_skip_due_to_depth(0)
    assert not policy.should_skip_due_to_depth(1)


def test_should_skip_due_to_robots_blocks_when_disallowed():
    pages_repo = MagicMock()
    robots_service = MagicMock()
    robots_service.allowed_by_robots.return_value = False
    policy = CrawlPolicy(pages_repo, robots_service)
    
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', robots=True, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert policy.should_skip_due_to_robots('http://example.com', context)
    robots_service.allowed_by_robots.assert_called_once_with('http://example.com', True)


def test_should_skip_due_to_robots_allows_when_permitted():
    pages_repo = MagicMock()
    robots_service = MagicMock()
    robots_service.allowed_by_robots.return_value = True
    policy = CrawlPolicy(pages_repo, robots_service)
    
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', robots=True, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert not policy.should_skip_due_to_robots('http://example.com', context)


def test_should_skip_due_to_robots_returns_false_when_no_service():
    pages_repo = MagicMock()
    policy = CrawlPolicy(pages_repo, robots_service=None)
    
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', robots=True, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert not policy.should_skip_due_to_robots('http://example.com', context)


def test_should_skip_due_to_refresh_skips_recent_page():
    pages_repo = MagicMock()
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    pages_repo.get_page_by_url.return_value = type('Page', (), {'fetched_at': yesterday})
    
    policy = CrawlPolicy(pages_repo)
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', refresh_days=7, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert policy.should_skip_due_to_refresh('http://example.com', context)


def test_should_skip_due_to_refresh_fetches_old_page():
    pages_repo = MagicMock()
    week_ago = (datetime.utcnow() - timedelta(days=8)).isoformat()
    pages_repo.get_page_by_url.return_value = type('Page', (), {'fetched_at': week_ago})
    
    policy = CrawlPolicy(pages_repo)
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', refresh_days=7, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert not policy.should_skip_due_to_refresh('http://example.com', context)


def test_should_skip_due_to_refresh_returns_false_when_no_refresh_days():
    pages_repo = MagicMock()
    policy = CrawlPolicy(pages_repo)
    
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', refresh_days=None, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert not policy.should_skip_due_to_refresh('http://example.com', context)


def test_should_skip_due_to_refresh_returns_false_when_page_not_found():
    pages_repo = MagicMock()
    pages_repo.get_page_by_url.return_value = None
    
    policy = CrawlPolicy(pages_repo)
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', refresh_days=7, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert not policy.should_skip_due_to_refresh('http://example.com', context)


def test_should_skip_due_to_refresh_returns_false_when_no_fetched_at():
    pages_repo = MagicMock()
    pages_repo.get_page_by_url.return_value = type('Page', (), {'fetched_at': None})
    
    policy = CrawlPolicy(pages_repo)
    cfg = CrawlerConfig(config_id=1, config_path='test.yml', refresh_days=7, fetch_mode="http")
    context = CrawlContext(cfg)
    
    assert not policy.should_skip_due_to_refresh('http://example.com', context)
