from __future__ import annotations

from typing import Optional, Protocol

from infracrawl.domain.http_response import HttpResponse


class Fetcher(Protocol):
    """Fetch a URL and return a normalized HTTP-like response.

    This is intentionally small so we can swap implementations later
    (e.g., requests-based vs headless-browser rendered HTML).
    """

    def fetch(self, url: str, stop_event=None) -> HttpResponse: ...


class HttpServiceFetcher:
    def __init__(self, http_service):
        self._http_service = http_service

    def fetch(self, url: str, stop_event=None) -> HttpResponse:
        return self._http_service.fetch(url)
