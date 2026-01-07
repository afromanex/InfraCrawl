import pytest
from unittest.mock import MagicMock
from infracrawl.services.crawler import Crawler

@pytest.fixture
def mock_repos():
    return {
        'pages_repo': MagicMock(),
        'links_repo': MagicMock(),
        'configs_repo': MagicMock(),
    }

def test_crawler_init_uses_injected_repos(mock_repos):
    crawler = Crawler(
        pages_repo=mock_repos['pages_repo'],
        links_repo=mock_repos['links_repo'],
        configs_repo=mock_repos['configs_repo'],
        delay=0.1,
        user_agent='TestAgent/1.0'
    )
    assert crawler.pages_repo is mock_repos['pages_repo']
    assert crawler.links_repo is mock_repos['links_repo']
    assert crawler.configs_repo is mock_repos['configs_repo']
    assert crawler.delay == 0.1
    assert crawler.user_agent == 'TestAgent/1.0'
