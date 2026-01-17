import pytest
from unittest.mock import MagicMock, call
from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.services.fetcher_factory import FetcherFactory
from infracrawl.services.configured_crawl_provider_factory import ConfiguredCrawlProviderFactory
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.crawl_result import CrawlResult
from infracrawl.domain.http_response import HttpResponse
from infracrawl.domain import CrawlSession

@pytest.fixture
def mock_repos():
    return {
        'pages_repo': MagicMock(),
        'links_repo': MagicMock(),
    }

def test_crawl_executor_init_uses_injected_collaborators(mock_repos):
    dummy_fetcher = MagicMock()
    fetcher_factory = FetcherFactory(http_fetcher=dummy_fetcher, headless_fetcher=dummy_fetcher)
    provider_factory = ConfiguredCrawlProviderFactory(
        fetcher_factory=fetcher_factory,
        pages_repo=mock_repos['pages_repo'],
        crawl_policy=MagicMock(),
        link_processor=MagicMock(),
        fetch_persist_service=MagicMock(),
    )
    executor = CrawlExecutor(
        provider_factory=provider_factory,
    )
    assert executor.provider_factory is provider_factory


def test_crawl_executor_updates_registry_with_page_count(mock_repos):
    """Test that the crawler updates the crawl registry with pages_fetched count."""
    # Setup
    dummy_fetcher = MagicMock()
    fetcher_factory = FetcherFactory(http_fetcher=dummy_fetcher, headless_fetcher=dummy_fetcher)
    
    mock_registry = MagicMock()
    # Mock the handle that registry.start() returns
    mock_handle = MagicMock()
    mock_handle.crawl_id = "test-crawl-123"
    mock_handle.stop_event = None
    mock_registry.start.return_value = mock_handle
    
    # Mock pages_repo to return a page_id on ensure_page
    mock_repos['pages_repo'].ensure_page.return_value = 1
    
    # Create a minimal config with one root URL
    config = CrawlerConfig(
        config_id=1,
        config_path="test.yml",
        root_urls=["http://example.com"],
        max_depth=1,
        fetch_mode="http",
        delay_seconds=0,
    )
    
    # Mock the fetcher to return a response
    mock_response = HttpResponse(status_code=200, text="<html><body>test</body></html>")
    dummy_fetcher.fetch.return_value = mock_response
    
    # Mock fetch_persist_service to return a page
    mock_page = MagicMock()
    mock_page.page_id = 1
    mock_fetch_persist = MagicMock(return_value=mock_page)
    
    # Mock crawl policy and link processor
    mock_crawl_policy = MagicMock()
    mock_crawl_policy.should_skip_due_to_depth.return_value = False
    mock_crawl_policy.should_skip_due_to_robots.return_value = False
    mock_crawl_policy.should_skip_due_to_refresh.return_value = False
    
    mock_link_processor = MagicMock()
    # Don't process any links so crawl stays simple
    mock_link_processor.process = MagicMock()
    
    provider_factory = ConfiguredCrawlProviderFactory(
        fetcher_factory=fetcher_factory,
        pages_repo=mock_repos['pages_repo'],
        crawl_policy=mock_crawl_policy,
        link_processor=mock_link_processor,
        fetch_persist_service=mock_fetch_persist,
    )
    
    # Create executor (no registry wired)
    executor = CrawlExecutor(
        provider_factory=provider_factory,
    )
    
    # Create session with registry injected
    session = CrawlSession(config, registry=mock_registry)
    # Manually call start_tracking since test doesn't use factory
    session.start_tracking()
    
    # Execute the crawl
    result = executor.crawl(session)
    
    # Verify that registry.start was called
    assert mock_registry.start.called, "registry.start should have been called"
    
    # Verify that registry.update was called with pages_fetched > 0
    assert mock_registry.update.called, "registry.update should have been called"
    # Check that at least one call included pages_fetched
    update_calls = mock_registry.update.call_args_list
    assert len(update_calls) > 0, "registry.update should be called at least once"
    # The final call should have pages_fetched set
    final_call = update_calls[-1]
    assert 'pages_fetched' in final_call[1], "registry.update should be called with pages_fetched parameter"
    assert final_call[1]['pages_fetched'] >= 1, "pages_fetched should be at least 1"
