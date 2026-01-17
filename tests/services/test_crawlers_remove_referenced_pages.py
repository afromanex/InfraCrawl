import pytest
from unittest.mock import MagicMock
from infracrawl.api.routers.crawlers import create_crawlers_router
from infracrawl.domain.config import CrawlerConfig


def test_remove_endpoint_deletes_all_referenced_pages():
    """Test that /crawlers/remove deletes all pages referenced by config pages, not just config's own pages.
    
    Scenario:
    - Config A has pages: 1, 2, 3
    - Page 1 (config A) -> links to Page 4 (no config_id or config B)
    - Page 2 (config A) -> links to Page 5 (no config_id or config B)
    - Page 3 (config A) -> no links
    
    When removing config A:
    - Should delete pages: 1, 2, 3, 4, 5 (all pages discovered by the config)
    - Should delete all links between them
    """
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
    
    # Config's own pages
    config_page_ids = [1, 2, 3]  # 3 pages from config
    mock_pages_repo.get_page_ids_by_config.return_value = config_page_ids
    
    # Pages referenced by config pages (including pages with no config_id)
    # Simulating that delete_links_for_page_ids returns all pages (config's + referenced)
    all_page_ids = [1, 2, 3, 4, 5]  # Also pages 4, 5 referenced
    mock_pages_repo.delete_pages_by_ids.return_value = 5  # All 5 pages deleted
    
    # Links deleted
    mock_links_repo.delete_links_for_page_ids.return_value = 7  # 7 links deleted
    
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
    
    # Find the remove endpoint function
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
    assert result["deleted_pages"] == 5, "Should delete all 5 pages (config + referenced)"
    assert result["deleted_links"] == 7
    
    # Verify repos were called correctly
    mock_config_service.get_config.assert_called_once_with("test.yml")
    mock_pages_repo.get_page_ids_by_config.assert_called_once_with(1)
    mock_links_repo.delete_links_for_page_ids.assert_called_once_with(config_page_ids)
    # Should call delete_pages with all pages (config's + referenced)
    call_args = mock_pages_repo.delete_pages_by_ids.call_args[0][0]
    assert set(call_args) == set(all_page_ids), f"Should delete all pages, got {call_args}"

