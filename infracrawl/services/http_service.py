import requests
from typing import Callable

from infracrawl.services.http_response import HttpResponse


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

    # TODO: No error handling - requests.get raises on DNS failure, SSL error, connection error, timeout
    # CLAUDE: Acknowledged - defer until needed in production
    def fetch(self, url: str) -> HttpResponse:
        """Fetch URL and return response with status code and body text."""
        headers = {"User-Agent": self.user_agent}
        resp = self.http_client(url, headers=headers, timeout=self.timeout)
        return HttpResponse(resp.status_code, resp.text)

    def fetch_robots(self, robots_url: str) -> HttpResponse:
        """Fetch robots.txt - delegates to fetch()."""
        return self.fetch(robots_url)
