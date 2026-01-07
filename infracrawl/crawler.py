import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser

from infracrawl import config
from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain import Link

logger = logging.getLogger(__name__)


pages_repo = PagesRepository()
links_repo = LinksRepository()
configs_repo = ConfigsRepository()

class Crawler:
    def __init__(self, delay=None, user_agent=None):
        self.delay = delay if delay is not None else config.CRAWL_DELAY
        self.user_agent = user_agent or config.USER_AGENT
        self._rp_cache: dict[str, RobotFileParser] = {}

    def fetch(self, url: str):
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.status_code, resp.text

    def _allowed_by_robots(self, url: str, robots_enabled: bool) -> bool:
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
                    r = requests.get(robots_url, headers={"User-Agent": self.user_agent}, timeout=5)
                    if r.status_code == 200:
                        rp.parse(r.text.splitlines())
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

    def extract_links(self, base_url: str, html: str):
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            abs_url = urljoin(base_url, href)
            urls.append((abs_url, a.get_text(strip=True)))
        return urls

    def _same_host(self, base: str, other: str) -> bool:
        try:
            b = urlparse(base).hostname
            o = urlparse(other).hostname
            return b == o or (b and o and o.endswith('.' + b))
        except Exception:
            return False

    def crawl(self, start_url: str, max_depth: int | None = None, config_id: int | None = None):
        """Depth-limited recursive crawl starting at `start_url`.

        Stores pages and links in the database. Pages discovered but not yet
        fetched are created with NULL content.
        """
        max_depth = max_depth if max_depth is not None else config.DEFAULT_DEPTH
        visited = set()

        # Load config once for the whole crawl to avoid repeated DB calls
        cfg_robots = True
        cfg_refresh_days = None
        if config_id is not None:
            cfg = configs_repo.get_config_by_id(config_id)
            if cfg:
                cfg_robots = cfg.robots
                cfg_refresh_days = cfg.refresh_days

        def _crawl_from(url: str, depth: int):
            if url in visited:
                logger.debug("Skipping (visited) %s", url)
                return
            visited.add(url)

            # ensure page row exists
            from_id = pages_repo.ensure_page(url)

            # if ensure_page created without config_id, we'll set config_id when upserting after fetch

            if depth < 0:
                logger.debug("Skipping (max depth reached) %s at depth %s", url, depth)
                return

            # Check robots and refresh_days
            cfg_robots = True
            cfg_refresh_days = None
            if config_id is not None:
                cfg = configs_repo.get_config_by_id(config_id)
                if cfg:
                    cfg_robots = cfg.robots
                    cfg_refresh_days = cfg.refresh_days

            if not self._allowed_by_robots(url, cfg_robots):
                logger.info("Skipping (robots) %s", url)
                return

            # Check refresh_days: skip fetching if recently fetched
            if cfg_refresh_days is not None:
                page = pages_repo.get_page_by_url(url)
                if page and page.fetched_at:
                    try:
                        last = page.fetched_at
                        if isinstance(last, str):
                            try:
                                last_dt = datetime.fromisoformat(last)
                            except Exception:
                                last_dt = None
                        else:
                            last_dt = last
                        if last_dt is not None:
                            try:
                                if last_dt.tzinfo is not None:
                                    last_dt_utc = last_dt.astimezone(timezone.utc).replace(tzinfo=None)
                                else:
                                    last_dt_utc = last_dt
                                delta_days = (datetime.utcnow() - last_dt_utc).days
                                if delta_days < int(cfg_refresh_days):
                                    logger.info("Skipping %s; fetched %s days ago (< %s)", url, delta_days, cfg_refresh_days)
                                    return
                            except Exception:
                                pass
                    except Exception:
                        pass

            try:
                status, body = self.fetch(url)
                fetched_at = datetime.utcnow().isoformat()
                page_id = pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id)
                logger.info("Fetched %s -> status %s, page_id=%s", url, status, page_id)
            except Exception as e:
                logger.warning("Failed to fetch %s: %s", url, e)
                return

            time.sleep(self.delay)

            links = self.extract_links(url, body)
            for link_url, anchor in links:
                if not self._same_host(start_url, link_url):
                    logger.debug("Skipping (external) %s -> not same host as %s", link_url, start_url)
                    continue
                to_id = pages_repo.ensure_page(link_url)
                link_obj = Link(link_id=None, link_from_id=from_id, link_to_id=to_id, anchor_text=anchor)
                links_repo.insert_link(link_obj)
                if depth - 1 >= 0:
                    _crawl_from(link_url, depth - 1)

        _crawl_from(start_url, max_depth)
