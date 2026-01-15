import pytest
from unittest.mock import MagicMock
from infracrawl.services.crawler import Crawler
from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.services.fetcher_factory import FetcherFactory

@pytest.fixture
def mock_repos():
    return {
        'pages_repo': MagicMock(),
        'links_repo': MagicMock(),
    }

def test_crawler_init_uses_injected_repos(mock_repos):
    dummy_fetcher = MagicMock()
    fetcher_factory = FetcherFactory(http_fetcher=dummy_fetcher, headless_fetcher=dummy_fetcher)
    executor = CrawlExecutor(
        pages_repo=mock_repos['pages_repo'],
        crawl_policy=MagicMock(),
        link_processor=MagicMock(),
        fetch_persist_service=MagicMock(),
        delay_seconds=0.1,
        fetcher_factory=fetcher_factory,
        extract_links_fn=MagicMock(),
    )
    crawler = Crawler(executor=executor)
    assert crawler._executor is executor
