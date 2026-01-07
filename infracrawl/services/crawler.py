import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from infracrawl.services.http_service import HttpService
from infracrawl.services.content_review_service import ContentReviewService
from infracrawl.services.robots_service import RobotsService

from infracrawl import config
from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain import Link

logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self, pages_repo=None, links_repo=None, configs_repo=None, delay=None, user_agent=None, http_service=None, content_review_service=None, robots_service=None):
        self.pages_repo = pages_repo or PagesRepository()
        self.links_repo = links_repo or LinksRepository()
        self.configs_repo = configs_repo or ConfigsRepository()
        self.delay = delay if delay is not None else config.CRAWL_DELAY
        self.user_agent = user_agent or config.USER_AGENT
        self.http_service = http_service or HttpService(self.user_agent)
        self.content_review_service = content_review_service or ContentReviewService()
        self.robots_service = robots_service or RobotsService(self.http_service, self.user_agent)

    def fetch(self, url: str):
        return self.http_service.fetch(url)

    def _allowed_by_robots(self, url: str, robots_enabled: bool) -> bool:
        return self.robots_service.allowed_by_robots(url, robots_enabled)

    def extract_links(self, base_url: str, html: str):
        return self.content_review_service.extract_links(base_url, html)

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
            cfg = self.configs_repo.get_config_by_id(config_id)
            if cfg:
                cfg_robots = cfg.robots
                cfg_refresh_days = cfg.refresh_days

        def _crawl_from(url: str, depth: int):
            if url in visited:
                logger.debug("Skipping (visited) %s", url)
                return
            visited.add(url)

            # ensure page row exists
            from_id = self.pages_repo.ensure_page(url)

            # if ensure_page created without config_id, we'll set config_id when upserting after fetch

            if depth < 0:
                logger.debug("Skipping (max depth reached) %s at depth %s", url, depth)
                return

            # Check robots and refresh_days
            cfg_robots = True
            cfg_refresh_days = None
            if config_id is not None:
                cfg = self.configs_repo.get_config_by_id(config_id)
                if cfg:
                    cfg_robots = cfg.robots
                    cfg_refresh_days = cfg.refresh_days

            if not self._allowed_by_robots(url, cfg_robots):
                logger.info("Skipping (robots) %s", url)
                return

            # Check refresh_days: skip fetching if recently fetched
            if cfg_refresh_days is not None:
                page = self.pages_repo.get_page_by_url(url)
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
                page_id = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id)
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
                to_id = self.pages_repo.ensure_page(link_url)
                link_obj = Link(link_id=None, link_from_id=from_id, link_to_id=to_id, anchor_text=anchor)
                self.links_repo.insert_link(link_obj)
                if depth - 1 >= 0:
                    _crawl_from(link_url, depth - 1)

        _crawl_from(start_url, max_depth)
