from infracrawl.services.robots_cache import RobotsCache
from urllib.robotparser import RobotFileParser
from unittest.mock import Mock


def test_cache_miss_returns_none():
    cache = RobotsCache()
    assert cache.get("https://example.com") is None


def test_cache_stores_and_retrieves_parser():
    cache = RobotsCache()
    parser = Mock(spec=RobotFileParser)
    cache.set("https://example.com", parser)
    assert cache.get("https://example.com") is parser


def test_cache_stores_none_for_failed_fetch():
    cache = RobotsCache()
    cache.set("https://example.com", None)
    assert cache.get("https://example.com") is None


def test_clear_removes_all_entries():
    cache = RobotsCache()
    cache.set("https://example.com", Mock())
    cache.set("https://other.com", Mock())
    cache.clear()
    assert cache.get("https://example.com") is None
    assert cache.get("https://other.com") is None
