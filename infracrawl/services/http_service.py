import requests
from typing import Callable


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
    # TODO: Returns status as int but callers treat it as str - API contract unclear 
    # CLAUDE: Status is int (correct). Callers like persist() incorrectly type it as str. Fix caller signatures.
    def fetch(self, url: str):
        headers = {"User-Agent": self.user_agent}
        resp = self.http_client(url, headers=headers, timeout=self.timeout)
        return resp.status_code, resp.text

    def fetch_robots(self, robots_url: str):
        """Fetch robots.txt - delegates to fetch()."""
        return self.fetch(robots_url)
