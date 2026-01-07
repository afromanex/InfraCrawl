from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

class RobotsService:
    def __init__(self, http_service, user_agent):
        self.http_service = http_service
        self.user_agent = user_agent
        self._rp_cache = {}

    def allowed_by_robots(self, url: str, robots_enabled: bool) -> bool:
        if not robots_enabled:
            return True
        try:
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            rp = self._rp_cache.get(base)
            if rp is None:
                rp = RobotFileParser()
                robots_url = urljoin(base, "/robots.txt")
                try:
                    status, robots_txt = self.http_service.fetch_robots(robots_url)
                    if status == 200:
                        rp.parse(robots_txt.splitlines())
                    else:
                        rp = None
                except Exception:
                    rp = None
                self._rp_cache[base] = rp
            if rp is None:
                return True
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True
