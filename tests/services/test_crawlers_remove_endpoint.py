import pytest
from unittest.mock import MagicMock
from infracrawl.api.routers.crawlers import create_crawlers_router
from infracrawl.domain.config import CrawlerConfig


def test_remove_endpoint_deletes_pages_and_links_for_config():
    """Test that /crawlers/remove deletes all pages and links for a config."""
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
    
    # Mock pages_repo to return page IDs and delete count
    page_ids = [1, 2, 3]  # 3 pages
    mock_pages_repo.get_page_ids_by_config.return_value = page_ids
    mock_pages_repo.delete_pages_by_ids.return_value = 3
    
    # Mock links_repo to return delete count
    mock_links_repo.delete_links_for_page_ids.return_value = 5  # 5 links deleted
    
    # Create router
    router = create_crawlers_router(
        pages_repo=mock_pages_repo,
        links_repo=mock_links_repo,
        config_service=mock_config_service,
        session_factory=MagicMock(),
        start_crawl_callback=MagicMock(),
        crawl_registry=None,
        crawls_repo=MagicMock(),
    )
    
    # Find the remove endpoint function - it's defined as @router.delete("/remove")
    remove_endpoint = None
    for route in router.routes:
        if hasattr(route, 'path') and route.path == '/crawlers/remove':
            remove_endpoint = route.endpoint
            break
    
    assert remove_endpoint is not None, "Remove endpoint should exist"
    
    # Call the endpoint with config parameter
    result = remove_endpoint(config="test.yml")
    
    # Verify response
    assert result["status"] == "removed"
    assert result["deleted_pages"] == 3
    assert result["deleted_links"] == 5
    
    # Verify that the repos were called correctly
    mock_config_service.get_config.assert_called_once_with("test.yml")
    mock_pages_repo.get_page_ids_by_config.assert_called_once_with(1)
    mock_links_repo.delete_links_for_page_ids.assert_called_once_with(page_ids)
    mock_pages_repo.delete_pages_by_ids.assert_called_once_with(page_ids)
