"""Tests for CrawlSessionFactory."""
import threading
from infracrawl.services.crawl_session_factory import CrawlSessionFactory
from infracrawl.domain import CrawlerConfig


def test_create_session_without_registry():
    """Factory creates session without registry tracking."""
    factory = CrawlSessionFactory(registry=None, visited_tracker_max_urls=10000)
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    
    session = factory.create(config)
    
    assert session.config == config
    assert session.crawl_id is None
    assert session.stop_event is None
    assert session.visited_tracker is not None
    assert session.pages_crawled == 0


def test_create_session_with_registry():
    """Factory creates session with registry tracking."""
    from unittest.mock import Mock
    
    # Mock registry that returns a handle with crawl_id and stop_event
    registry = Mock()
    handle = Mock()
    handle.crawl_id = "test-crawl-123"
    handle.stop_event = threading.Event()
    registry.start.return_value = handle
    
    factory = CrawlSessionFactory(registry=registry, visited_tracker_max_urls=10000)
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    
    session = factory.create(config)
    
    # Verify registry was called
    registry.start.assert_called_once_with(
        config_name='test.yml',
        config_id=1
    )
    
    # Verify session has registry tracking
    assert session.config == config
    assert session.crawl_id == "test-crawl-123"
    assert session.stop_event is handle.stop_event
    assert session.visited_tracker is not None


def test_session_has_correct_max_depth():
    """Session inherits max_depth from config."""
    factory = CrawlSessionFactory(registry=None, visited_tracker_max_urls=10000)
    config = CrawlerConfig(
        config_id=1, 
        config_path='test.yml', 
        fetch_mode='http',
        max_depth=5
    )
    
    session = factory.create(config)
    
    assert session.max_depth == 5
    assert session.current_depth is None  # Not set until crawl starts


def test_visited_tracker_respects_max_urls():
    """Session's visited tracker is configured with max_urls."""
    factory = CrawlSessionFactory(registry=None, visited_tracker_max_urls=500)
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    
    session = factory.create(config)
    
    # Verify tracker has the limit (internal state check)
    assert session.visited_tracker._max_size == 500
