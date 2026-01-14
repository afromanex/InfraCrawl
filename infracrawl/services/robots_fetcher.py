from urllib.robotparser import RobotFileParser


class RobotsFetcher:
    """Fetch robots.txt content and return a parsed RobotFileParser or None.

    Uses an `http_service` with a `fetch_robots(url)` method that returns
    an HttpResponse.
    """
    def __init__(self, http_service):
        self.http_service = http_service

    def fetch(self, robots_url: str):
        try:
            response = self.http_service.fetch_robots(robots_url)
            if response.status_code == 200 and response.text:
                robots_parser = RobotFileParser()
                robots_parser.parse(response.text.splitlines())
                return robots_parser
            return None
        except Exception:
            import logging
            logging.exception("Error fetching/parsing robots.txt from %s", robots_url)
            return None
