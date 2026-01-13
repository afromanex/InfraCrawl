from urllib.parse import urljoin, urlparse

from infracrawl.services.robots_fetcher import RobotsFetcher


class RobotsService:
    def __init__(self, http_service, user_agent, robots_fetcher: RobotsFetcher = None):
        # Backwards-compatible: callers may still pass an http_service with fetch_robots
        self.http_service = http_service
        self.user_agent = user_agent
        self._rp_cache = {}
        self.robots_fetcher = robots_fetcher or RobotsFetcher(http_service)

    def allowed_by_robots(self, url: str, robots_enabled: bool) -> bool:
        if not robots_enabled:
            return True
        try:
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            robots_parser = self._rp_cache.get(base)
            if robots_parser is None:
                robots_url = urljoin(base, "/robots.txt")
                try:
                    robots_parser = self.robots_fetcher.fetch(robots_url)
                except Exception:
                    import logging
                    logging.exception("Error fetching robots.txt from %s", robots_url)
                    robots_parser = None
                self._rp_cache[base] = robots_parser
            if robots_parser is None:
                return True
            return robots_parser.can_fetch(self.user_agent, url)
        except Exception:
            import logging
            logging.exception("Error checking robots.txt permission for %s", url)
            return True
