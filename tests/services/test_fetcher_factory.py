import pytest

from infracrawl.services.fetcher_factory import FetcherFactory
from infracrawl.domain.config import CrawlerConfig


class _DummyFetcher:
    def fetch(self, url: str, stop_event=None):
        return url


def _make_config(fetch_mode: str) -> CrawlerConfig:
    return CrawlerConfig(
        config_id=1,
        config_path="test",
        root_urls=["http://example.test"],
        fetch_mode=fetch_mode,
    )


def test_fetcher_factory_requires_fetch_mode():
    factory = FetcherFactory(http_fetcher=_DummyFetcher(), headless_fetcher=_DummyFetcher())
    with pytest.raises(ValueError, match="fetch_mode is required"):
        factory.get(_make_config(""))


def test_fetcher_factory_selects_http():
    factory = FetcherFactory(http_fetcher=_DummyFetcher(), headless_fetcher=_DummyFetcher())
    assert factory.get(_make_config(" http ")).fetch("x") == "x"


def test_fetcher_factory_unknown_mode_raises():
    factory = FetcherFactory(http_fetcher=_DummyFetcher(), headless_fetcher=_DummyFetcher())
    with pytest.raises(ValueError, match="Unknown fetch_mode"):
        factory.get(_make_config("nope"))
