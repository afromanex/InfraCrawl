from urllib.robotparser import RobotFileParser


class RobotsFetcher:
    """Fetch robots.txt content and return a parsed RobotFileParser or None.

    Uses an `http_service` with a `fetch_robots(url)` method that returns
    `(status_code, body)`.
    """
    def __init__(self, http_service):
        self.http_service = http_service

    def fetch(self, robots_url: str):
        try:
            status, body = self.http_service.fetch_robots(robots_url)
            if status == 200 and body:
                robots_parser = RobotFileParser()
                robots_parser.parse(body.splitlines())
                return robots_parser
            return None
        except Exception:
            import logging
            logging.exception("Error fetching/parsing robots.txt from %s", robots_url)
            return None
