import pytest

from infracrawl.services.fetcher_factory import FetcherFactory


class _DummyFetcher:
    def fetch(self, url: str, stop_event=None):
        return url


def test_fetcher_factory_requires_fetch_mode():
    factory = FetcherFactory(http_fetcher=_DummyFetcher(), headless_fetcher=_DummyFetcher())
    with pytest.raises(ValueError, match="fetch_mode is required"):
        factory.get("")


def test_fetcher_factory_selects_http():
    factory = FetcherFactory(http_fetcher=_DummyFetcher(), headless_fetcher=_DummyFetcher())
    assert factory.get(" http ").fetch("x") == "x"


def test_fetcher_factory_unknown_mode_raises():
    factory = FetcherFactory(http_fetcher=_DummyFetcher(), headless_fetcher=_DummyFetcher())
    with pytest.raises(ValueError, match="Unknown fetch_mode"):
        factory.get("nope")
