import pytest
from unittest.mock import MagicMock
from infracrawl.services.crawl_session_resume_factory import CrawlSessionResumeFactory
from infracrawl.domain.config import CrawlerConfig


@pytest.fixture
def mock_pages_repo():
    return MagicMock()


@pytest.fixture
def factory(mock_pages_repo):
    return CrawlSessionResumeFactory(
        pages_repo=mock_pages_repo,
        visited_tracker_max_urls=100_000,
    )


def test_rebuild_loads_visited_urls_from_database(factory, mock_pages_repo):
    """rebuild() should load visited URLs from database and populate tracker."""
    config = CrawlerConfig(
        config_id=42,
        config_path="test.yml",
        root_urls=["http://example.com"],
        max_depth=2,
        fetch_mode="http",
        delay_seconds=0,
    )
    
    # Mock the pages repo to return some visited URLs
    mock_pages_repo.get_visited_urls_by_config.return_value = [
        "http://example.com",
        "http://example.com/page1",
        "http://example.com/page2",
    ]
    
    session = factory.rebuild(config)
    
    # Verify pages repo was called with correct config_id
    mock_pages_repo.get_visited_urls_by_config.assert_called_once_with(42)
    
    # Verify session has visited tracker pre-populated
    assert session.visited_tracker is not None
    assert session.visited_tracker.is_visited("http://example.com")
    assert session.visited_tracker.is_visited("http://example.com/page1")
    assert session.visited_tracker.is_visited("http://example.com/page2")
    assert not session.visited_tracker.is_visited("http://example.com/page3")


def test_rebuild_handles_config_without_id(factory, mock_pages_repo):
    """rebuild() should handle configs without config_id gracefully."""
    config = CrawlerConfig(
        config_id=None,
        config_path="test.yml",
        root_urls=["http://example.com"],
        max_depth=2,
        fetch_mode="http",
        delay_seconds=0,
    )
    
    session = factory.rebuild(config)
    
    # Should not call pages repo if config_id is None
    mock_pages_repo.get_visited_urls_by_config.assert_not_called()
    
    # Should still create a valid session with empty tracker
    assert session.visited_tracker is not None
    assert not session.visited_tracker.is_visited("http://example.com")


def test_rebuild_with_registry_starts_tracking(mock_pages_repo):
    """rebuild() should start tracking if registry is configured."""
    mock_registry = MagicMock()
    mock_handle = MagicMock()
    mock_handle.crawl_id = "resumed-crawl-123"
    mock_handle.stop_event = MagicMock()
    mock_registry.start.return_value = mock_handle
    
    factory = CrawlSessionResumeFactory(
        pages_repo=mock_pages_repo,
        registry=mock_registry,
    )
    
    config = CrawlerConfig(
        config_id=1,
        config_path="test.yml",
        root_urls=["http://example.com"],
        max_depth=2,
        fetch_mode="http",
        delay_seconds=0,
    )
    
    mock_pages_repo.get_visited_urls_by_config.return_value = []
    
    session = factory.rebuild(config)
    
    # Verify tracking was started
    mock_registry.start.assert_called_once()
    assert session.crawl_id == "resumed-crawl-123"

