from infracrawl.services.robots_service import RobotsService
import pytest
from unittest.mock import MagicMock

class DummyHttp:
    def __init__(self, status, text):
        self.status = status
        self.text = text
        self.called_urls = []
    def fetch_robots(self, url):
        self.called_urls.append(url)
        return self.status, self.text

def test_allowed_by_robots_allows_if_disabled():
    svc = RobotsService(DummyHttp(200, ''), user_agent='TestAgent')
    assert svc.allowed_by_robots('http://example.com', robots_enabled=False)

def test_allowed_by_robots_allows_if_no_robots():
    svc = RobotsService(DummyHttp(404, ''), user_agent='TestAgent')
    assert svc.allowed_by_robots('http://example.com', robots_enabled=True)

def test_allowed_by_robots_blocks_disallowed():
    robots_txt = 'User-agent: *\nDisallow: /private'
    svc = RobotsService(DummyHttp(200, robots_txt), user_agent='TestAgent')
    # Should block /private
    assert not svc.allowed_by_robots('http://example.com/private', robots_enabled=True)
    # Should allow /public
    assert svc.allowed_by_robots('http://example.com/public', robots_enabled=True)
