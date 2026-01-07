import logging
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from infracrawl.services.http_service import HttpService
from infracrawl.services.content_review_service import ContentReviewService
from infracrawl.services.robots_service import RobotsService
from infracrawl.services.link_processor import LinkProcessor

from infracrawl import config
from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain import Link
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.crawl_context import CrawlContext

logger = logging.getLogger(__name__)


class Crawler:
    def _should_skip_due_to_depth(self, context: CrawlContext, depth: int) -> bool:
        if depth < 0:
            logger.debug("Skipping (max depth reached) at depth %s", depth)
            return True
        return False

    def _should_skip_due_to_robots(self, url: str, context: CrawlContext) -> bool:
        cfg_robots = True
        if context and context.config is not None:
            cfg_robots = context.config.robots
        if not self._allowed_by_robots(url, cfg_robots):
            logger.info("Skipping (robots) %s", url)
            return True
        return False

    def _should_skip_due_to_refresh(self, url: str, context: CrawlContext) -> bool:
        cfg_refresh_days = None
        if context and context.config is not None:
            cfg_refresh_days = context.config.refresh_days
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
                                return True
                        except Exception:
                            pass
                except Exception:
                    pass
        return False

    def _fetch_and_store(self, url: str, context: CrawlContext):
        try:
            status, body = self.fetch(url)
            fetched_at = datetime.utcnow().isoformat()
            config_id = context.config.config_id if (context and context.config) else None
            page_id = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id)
            logger.info("Fetched %s -> status %s, page_id=%s", url, status, page_id)
            return body
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            return None

    def _process_links(self, url: str, body: str, from_id: int, context: CrawlContext, depth: int, _crawl_from=None):
        # Delegate link extraction, persistence and scheduling to LinkProcessor
        # Crawl callback prefers direct method but falls back to supplied callback
        def cb(link_url, next_depth):
            if _crawl_from is not None:
                _crawl_from(link_url, next_depth)
            else:
                self._crawl_from(link_url, next_depth, context)

        self.link_processor.process_links(context.current_root, url, body, from_id, context, depth, crawl_callback=cb, extract_links_fn=self.extract_links)
    def __init__(self, pages_repo=None, links_repo=None, configs_repo=None, delay=None, user_agent=None, http_service=None, content_review_service=None, robots_service=None, link_processor=None):
        self.pages_repo = pages_repo or PagesRepository()
        self.links_repo = links_repo or LinksRepository()
        self.configs_repo = configs_repo or ConfigsRepository()
        self.delay = delay if delay is not None else config.CRAWL_DELAY
        self.user_agent = user_agent or config.USER_AGENT
        self.http_service = http_service or HttpService(self.user_agent)
        self.content_review_service = content_review_service or ContentReviewService()
        self.robots_service = robots_service or RobotsService(self.http_service, self.user_agent)
        self.link_processor = link_processor or LinkProcessor(self.content_review_service, self.pages_repo, self.links_repo)

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

    def crawl(self, config: CrawlerConfig):
        """Crawl using the provided `CrawlerConfig` object.

        Iterates `config.root_urls` and performs depth-limited crawling from
        each root, using `config.max_depth` and other config options.
        """
        if config is None:
            raise ValueError("config is required for crawl")
        # Build context from the provided config
        context = CrawlContext(config)
        # Ensure max_depth is set
        if context.max_depth is None:
            context.max_depth = config.DEFAULT_DEPTH

        roots = getattr(context.config, 'root_urls', []) or []
        for ru in roots:
            context.set_root(ru)
            self._crawl_from(ru, context.max_depth, context)

    def _crawl_from(self, url: str, depth: int, context: CrawlContext):
        if context.is_visited(url):
            logger.debug("Skipping (visited) %s", url)
            return
        context.mark_visited(url)

        from_id = self.pages_repo.ensure_page(url)

        if self._should_skip_due_to_depth(context, depth):
            return
        if self._should_skip_due_to_robots(url, context):
            return
        if self._should_skip_due_to_refresh(url, context):
            return

        body = self._fetch_and_store(url, context)
        if body is None:
            return

        time.sleep(self.delay)
        self._process_links(url, body, from_id, context, depth, None)

        
