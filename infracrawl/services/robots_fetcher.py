from urllib.robotparser import RobotFileParser

from infracrawl.exceptions import HttpFetchError


class RobotsFetcher:
    """Fetch robots.txt content and return a parsed RobotFileParser or None.

    Uses an `http_service` with a `fetch_robots(url)` method that returns
    an HttpResponse.
    """
    def __init__(self, http_service):
        self.http_service = http_service

    def fetch(self, robots_url: str):
        import logging

        try:
            response = self.http_service.fetch_robots(robots_url)
        except HttpFetchError:
            logging.exception("Network error fetching robots.txt from %s", robots_url)
            return None

        if response.status_code != 200 or not response.text:
            return None

        try:
            robots_parser = RobotFileParser()
            robots_parser.parse(response.text.splitlines())
            return robots_parser
        except Exception:
            logging.exception("Error parsing robots.txt from %s", robots_url)
            return None
