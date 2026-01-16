import pytest
from unittest.mock import MagicMock
from infracrawl.api.routers.crawlers import create_crawlers_router
from infracrawl.domain.config import CrawlerConfig


def test_get_config_stats_returns_page_and_link_counts():
    """Test that stats endpoint returns page and link counts."""
    # Setup mocks
    mock_pages_repo = MagicMock()
    mock_links_repo = MagicMock()
    mock_config_service = MagicMock()
    
    # Create a test config
    config = CrawlerConfig(
        config_id=1,
        config_path="test.yml",
        root_urls=["http://example.com"],
        max_depth=1,
        fetch_mode="http",
    )
    
    # Mock config_service.get_config to return the test config
    mock_config_service.get_config.return_value = config
    
    # Mock pages_repo to return page IDs
    page_ids = [1, 2, 3]  # 3 pages
    mock_pages_repo.get_page_ids_by_config.return_value = page_ids
    
    # Mock links_repo to return link count
    mock_links_repo.count_links_for_page_ids.return_value = 5  # 5 links
    
    # Create router
    router = create_crawlers_router(
        pages_repo=mock_pages_repo,
        links_repo=mock_links_repo,
        config_service=mock_config_service,
        start_crawl_callback=MagicMock(),
        crawl_registry=None,
        crawls_repo=MagicMock(),
    )
    
    # Find the stats endpoint function by name
    stats_endpoint = None
    for route in router.routes:
        if hasattr(route, 'path') and '/stats/' in route.path:
            stats_endpoint = route.endpoint
            break
    
    assert stats_endpoint is not None, "Stats endpoint should exist"
    
    # Call the endpoint
    result = stats_endpoint("test.yml")
    
    # Verify response
    assert result["config_path"] == "test.yml"
    assert result["pages"] == 3
    assert result["links"] == 5
    
    # Verify that the repos were called correctly
    mock_config_service.get_config.assert_called_once_with("test.yml")
    mock_pages_repo.get_page_ids_by_config.assert_called_once_with(1)
    mock_links_repo.count_links_for_page_ids.assert_called_once_with(page_ids)
