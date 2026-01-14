from urllib.parse import urljoin, urlparse
import logging
from typing import Optional

from infracrawl.services.robots_fetcher import RobotsFetcher
from infracrawl.services.robots_cache import RobotsCache


class RobotsService:
    """
    Service for checking robots.txt permissions.
    
    Orchestrates fetching, caching, and permission checking for robots.txt files.
    Cache is now injectable for testing and independent cache strategy changes.
    """
    
    def __init__(self, http_service, user_agent: str, 
                 robots_fetcher: Optional[RobotsFetcher] = None,
                 cache: Optional[RobotsCache] = None):
        # Backwards-compatible: callers may still pass an http_service with fetch_robots
        self.http_service = http_service
        self.user_agent = user_agent
        self.robots_fetcher = robots_fetcher if robots_fetcher is not None else RobotsFetcher(http_service)
        self.cache = cache if cache is not None else RobotsCache()

    def allowed_by_robots(self, url: str, robots_enabled: bool) -> bool:
        if not robots_enabled:
            return True
        try:
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            robots_parser = self.cache.get(base)
            if robots_parser is None:
                robots_url = urljoin(base, "/robots.txt")
                try:
                    robots_parser = self.robots_fetcher.fetch(robots_url)
                except Exception:
                    logging.exception("Error fetching robots.txt from %s", robots_url)
                    robots_parser = None
                self.cache.set(base, robots_parser)
            if robots_parser is None:
                return True
            return robots_parser.can_fetch(self.user_agent, url)
        except Exception:
            logging.exception("Error checking robots.txt permission for %s", url)
            return True
