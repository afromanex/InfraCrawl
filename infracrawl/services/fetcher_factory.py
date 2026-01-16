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

    def get(self, fetch_mode: str, config=None) -> Fetcher:
        if fetch_mode is None or (isinstance(fetch_mode, str) and fetch_mode.strip() == ""):
            raise ValueError("fetch_mode is required")
        mode = fetch_mode.strip().lower()
        if mode == "http":
            # Return configured HTTP fetcher if options provided
            if config and hasattr(config, 'http_options') and config.http_options:
                from infracrawl.services.fetcher import HttpServiceFetcher
                from infracrawl.services.http_service import HttpService
                # Extract timeout, convert ms to seconds
                timeout = config.http_options.get("timeout_ms", 10000) / 1000
                # Get user_agent and http_client from base fetcher
                base_service = self.http_fetcher._http_service
                import requests
                configured_service = HttpService(
                    user_agent=base_service.user_agent,
                    http_client=requests.get,
                    timeout=int(timeout)
                )
                return HttpServiceFetcher(configured_service)
            return self.http_fetcher
        if mode == "headless_chromium":
            # Return configured headless fetcher if options provided
            if config and hasattr(config, 'headless_options') and config.headless_options:
                from infracrawl.services.headless_browser_fetcher import PlaywrightHeadlessFetcher, PlaywrightHeadlessOptions
                options = config.headless_options
                # Get base fetcher user_agent
                base_user_agent = self.headless_fetcher._user_agent
                configured_options = PlaywrightHeadlessOptions(
                    timeout_ms=options.get("timeout_ms", 10000),
                    wait_until=options.get("wait_until", "networkidle")
                )
                return PlaywrightHeadlessFetcher(user_agent=base_user_agent, options=configured_options)
            return self.headless_fetcher
        raise ValueError(f"Unknown fetch_mode: {fetch_mode!r}")
