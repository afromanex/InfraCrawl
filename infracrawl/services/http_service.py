import requests

# TODO: Dependency Inversion violation - hardcoded requests.get() call. Risk: cannot swap to httpx, aiohttp, or async without rewriting; testing requires real HTTP or monkey-patching. Refactor: inject IHttpClient protocol with fetch(url, headers, timeout) method; requests becomes adapter.
# RESPONSE: Valid point. However, for simplicity we will keep it as is for now.
class HttpService:
    def __init__(self, user_agent: str, timeout: int = 10):
        self.user_agent = user_agent
        self.timeout = timeout

    # TODO: No error handling - requests.get raises on DNS failure, SSL error, connection error, timeout
    # CLAUDE: Acknowledged - defer until needed in production
    # TODO: Returns status as int but callers treat it as str - API contract unclear 
    # CLAUDE: Status is int (correct). Callers like persist() incorrectly type it as str. Fix caller signatures.
    def fetch(self, url: str):
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        return resp.status_code, resp.text

    def fetch_robots(self, robots_url: str):
        """Fetch robots.txt - delegates to fetch()."""
        return self.fetch(robots_url)
