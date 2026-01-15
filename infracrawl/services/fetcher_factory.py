from __future__ import annotations

from dataclasses import dataclass

from infracrawl.services.fetcher import Fetcher


class DisabledHeadlessFetcher:
    def fetch(self, url: str, stop_event=None):
        raise RuntimeError(
            "fetch_mode=headless_chromium requested but headless fetching is not configured"
        )


@dataclass(frozen=True)
class FetcherFactory:
    http_fetcher: Fetcher
    headless_fetcher: Fetcher

    def get(self, fetch_mode: str) -> Fetcher:
        if fetch_mode is None or (isinstance(fetch_mode, str) and fetch_mode.strip() == ""):
            raise ValueError("fetch_mode is required")
        mode = fetch_mode.strip().lower()
        if mode == "http":
            return self.http_fetcher
        if mode == "headless_chromium":
            return self.headless_fetcher
        raise ValueError(f"Unknown fetch_mode: {fetch_mode!r}")
