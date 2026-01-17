import importlib.util
import pytest

from infracrawl.services.headless_browser_fetcher import PlaywrightHeadlessFetcher


class _StopEvent:
    def __init__(self, *, is_set: bool):
        self._is_set = is_set

    def is_set(self) -> bool:
        return self._is_set


def test_headless_fetcher_respects_stop_event_before_import():
    fetcher = PlaywrightHeadlessFetcher(user_agent="ua")
    with pytest.raises(RuntimeError, match="Fetch cancelled"):
        fetcher.fetch("http://example.com", stop_event=_StopEvent(is_set=True))


def test_headless_fetcher_raises_if_playwright_missing():
    # If Playwright is installed in this environment, skip this assertion.
    if importlib.util.find_spec("playwright") is not None:
        pytest.skip("playwright is installed; missing-import behavior not applicable")

    fetcher = PlaywrightHeadlessFetcher(user_agent="ua")
    with pytest.raises(RuntimeError, match="Playwright is not installed"):
        fetcher.fetch("http://example.com")
