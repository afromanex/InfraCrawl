import requests
from typing import Callable

from infracrawl.domain.http_response import HttpResponse
from infracrawl.exceptions import HttpFetchError


class HttpService:
    """
    HTTP client wrapper for fetching web pages.
    
    Requires http_client callable for dependency injection (DIP compliance).
    This enables easy testing without patching and allows swapping HTTP libraries.
    """
    
    def __init__(self, user_agent: str, http_client: Callable, timeout: int = 10):
        self.user_agent = user_agent
        self.timeout = timeout
        self.http_client = http_client

    def fetch(self, url: str) -> HttpResponse:
        """Fetch URL and return response with status code, body text, and Content-Type."""
        headers = {"User-Agent": self.user_agent}
        try:
            resp = self.http_client(url, headers=headers, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            raise HttpFetchError(url, e) from e
        
        # Extract Content-Type if response has headers; let real exceptions bubble up.
        ct = None
        if hasattr(resp, 'headers'):
            ct = resp.headers.get('Content-Type')
        
        return HttpResponse(resp.status_code, resp.text, ct)

    def fetch_robots(self, robots_url: str) -> HttpResponse:
        """Fetch robots.txt - delegates to fetch()."""
        return self.fetch(robots_url)
