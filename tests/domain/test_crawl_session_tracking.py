"""Tests for CrawlSession tracking lifecycle methods."""
import threading
from unittest.mock import Mock
from infracrawl.domain import CrawlSession, CrawlerConfig


def test_session_without_registry_tracking_is_noop():
    """Session without registry can be created and tracking methods don't error."""
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    session = CrawlSession(config, registry=None)
    
    # Should not error when registry is None
    session.start_tracking()
    session.update_progress()
    session.finish_tracking()
    
    # Should not have tracking IDs
    assert session.crawl_id is None
    assert session.stop_event is not None  # Always created locally


def test_session_start_tracking_calls_registry_start():
    """start_tracking() calls registry.start() and stores handle."""
    registry = Mock()
    handle = Mock()
    handle.crawl_id = "crawl-abc-123"
    handle.stop_event = threading.Event()
    registry.start.return_value = handle
    
    config = CrawlerConfig(config_id=42, config_path='prod.yml', fetch_mode='http')
    session = CrawlSession(config, registry=registry)
    
    session.start_tracking()
    
    # Verify registry.start was called with correct params
    registry.start.assert_called_once_with(
        config_name='prod.yml',
        config_id=42
    )
    
    # Verify session stored the tracking details
    assert session.crawl_id == "crawl-abc-123"
    assert session.stop_event is handle.stop_event


def test_session_update_progress_calls_registry_update():
    """update_progress() reports current page count to registry."""
    registry = Mock()
    handle = Mock()
    handle.crawl_id = "crawl-xyz-456"
    handle.stop_event = threading.Event()
    registry.start.return_value = handle
    
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    session = CrawlSession(config, registry=registry)
    session.start_tracking()
    
    # Simulate pages being crawled
    session.pages_crawled = 15
    session.links_discovered = 42
    session.current_root = "http://example.com/page"
    
    session.update_progress()
    
    # Verify registry.update was called with current stats
    registry.update.assert_called_once_with(
        "crawl-xyz-456",
        pages_fetched=15,
        links_found=42,
        current_url="http://example.com/page"
    )


def test_session_update_progress_without_start_is_noop():
    """update_progress() before start_tracking() doesn't error."""
    registry = Mock()
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    session = CrawlSession(config, registry=registry)
    
    # Don't call start_tracking()
    session.pages_crawled = 10
    session.update_progress()
    
    # Should not have called registry since crawl_id is None
    registry.update.assert_not_called()


def test_session_finish_tracking_calls_registry_finish():
    """finish_tracking() marks crawl as complete in registry."""
    registry = Mock()
    handle = Mock()
    handle.crawl_id = "crawl-done-789"
    handle.stop_event = threading.Event()
    registry.start.return_value = handle
    
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    session = CrawlSession(config, registry=registry)
    session.start_tracking()
    
    session.finish_tracking(status="finished")
    
    # Verify registry.finish was called
    registry.finish.assert_called_once_with(
        "crawl-done-789",
        status="finished",
        error=None
    )


def test_session_finish_tracking_with_error():
    """finish_tracking() can report errors."""
    registry = Mock()
    handle = Mock()
    handle.crawl_id = "crawl-fail-999"
    handle.stop_event = threading.Event()
    registry.start.return_value = handle
    
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    session = CrawlSession(config, registry=registry)
    session.start_tracking()
    
    session.finish_tracking(status="failed", error="Network timeout")
    
    # Verify error was passed through
    registry.finish.assert_called_once_with(
        "crawl-fail-999",
        status="failed",
        error="Network timeout"
    )


def test_session_finish_tracking_without_start_is_noop():
    """finish_tracking() before start_tracking() doesn't error."""
    registry = Mock()
    config = CrawlerConfig(config_id=1, config_path='test.yml', fetch_mode='http')
    session = CrawlSession(config, registry=registry)
    
    # Don't call start_tracking()
    session.finish_tracking()
    
    # Should not have called registry since crawl_id is None
    registry.finish.assert_not_called()
