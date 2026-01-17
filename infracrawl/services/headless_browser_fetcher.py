from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

from infracrawl.domain.http_response import HttpResponse


@dataclass(frozen=True)
class PlaywrightHeadlessOptions:
    timeout_ms: int = 10_000
    wait_until: str = "networkidle"  # domcontentloaded | load | networkidle


class PlaywrightHeadlessFetcher:
    """Headless browser fetcher backed by Playwright.

    This fetcher renders JavaScript-heavy pages and returns the final DOM HTML
    via page.content().

    Notes:
    - This implementation is intentionally simple: it launches a browser per
      request. It can be optimized later by reusing a browser/context.
    - Playwright is imported lazily so non-headless installs still work.
    """

    def __init__(self, *, user_agent: str, options: Optional[PlaywrightHeadlessOptions] = None):
        self._user_agent = user_agent
        self._options = options or PlaywrightHeadlessOptions()
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="playwright")

    def _fetch_sync(self, url: str, stop_event) -> HttpResponse:
        """Internal synchronous fetch implementation."""
        if stop_event is not None and getattr(stop_event, "is_set", lambda: False)():
            raise RuntimeError("Fetch cancelled")

        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Headless fetch requested but Playwright is not installed. "
                "Install 'playwright' and run 'python -m playwright install chromium'."
            ) from e

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=self._user_agent)
                page = context.new_page()
                resp = page.goto(url, wait_until=self._options.wait_until, timeout=self._options.timeout_ms)
                status = 0
                try:
                    status = int(resp.status) if resp is not None else 0
                except Exception:
                    status = 0
                html = page.content()
                return HttpResponse(status_code=status, text=html)
            finally:
                try:
                    browser.close()
                except Exception:
                    pass

    def fetch(self, url: str, stop_event=None) -> HttpResponse:
        """Fetch a URL using Playwright in a thread to avoid asyncio loop conflicts."""
        try:
            # Check if we're in an asyncio event loop
            loop = asyncio.get_running_loop()
            # We're in an asyncio context, run in thread pool
            import concurrent.futures
            future = self._executor.submit(self._fetch_sync, url, stop_event)
            return future.result()
        except RuntimeError:
            # Not in an asyncio loop, call directly
            return self._fetch_sync(url, stop_event)
