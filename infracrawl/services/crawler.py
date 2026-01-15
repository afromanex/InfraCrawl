import logging
import time
from datetime import datetime
from typing import Optional
import requests
from infracrawl.utils.datetime_utils import parse_to_utc_naive
from urllib.parse import urlparse

from infracrawl.services.http_service import HttpService
from infracrawl.services.fetcher import Fetcher, HttpServiceFetcher
from infracrawl.services.content_review_service import ContentReviewService
from infracrawl.services.robots_service import RobotsService
from infracrawl.services.link_processor import LinkProcessor
from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.services.crawl_policy import CrawlPolicy

from infracrawl import config as env
from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.crawl_result import CrawlResult

logger = logging.getLogger(__name__)

# TODO: Single Responsibility violation - Crawler orchestrates crawling, enforces robots.txt, manages depth, handles refresh logic, extracts links, persists pages. Risk: any change to one concern (e.g., robots policy) requires modifying Crawler. Refactor: extract CrawlOrchestrator as thin coordinator; push depth/robots/refresh checks into separate policy objects.
# RESPONSE: We can extract to RobotsTxtService, but for simplicity we will keep it as is for now.
class Crawler:
    def _is_stopped(self, stop_event) -> bool:
        """Check if stop event is set."""
        return stop_event is not None and getattr(stop_event, 'is_set', lambda: False)()

    def _fetch_and_store(self, url: str, context: CrawlContext, stop_event=None):
        """Fetch a URL and persist the result using `FetchPersistService`.

        Returns the response body on success, or `None` on failure.
        """
        # Use the overridable `fetch` method so tests and subclasses can intercept network I/O
        try:
            # check for cooperative cancellation before network I/O
            if self._is_stopped(stop_event):
                logger.info("Fetch cancelled for %s", url)
                return None
            response = self.fetch(url, stop_event=stop_event)
        except Exception as e:
            logger.error("Fetch error for %s: %s", url, e, exc_info=True)
            return None

        fetched_at = datetime.utcnow().isoformat()
        try:
            page = self.fetch_persist_service.extract_and_persist(url, response.status_code, response.text, fetched_at, context=context)
            logger.info("Fetched %s -> status %s, page_id=%s", url, response.status_code, getattr(page, 'page_id', None))
        except Exception as e:
            logger.error("Storage error while saving %s: %s", url, e, exc_info=True)
            return None

        try:
            sc = int(response.status_code)
            if sc < 200 or sc >= 300:
                logger.warning("Non-success status for %s: %s", url, response.status_code)
        except Exception:
            logger.exception("Error parsing status code for %s: %s", url, response.status_code)
            pass

        return response.text

    def _process_links(self, url: str, body: str, from_id: int, context: CrawlContext, depth: int, _crawl_from=None, stop_event=None) -> tuple[int, bool]:
        """Extract and process links from page body.
        
        Returns:
            (pages_crawled, stopped) tuple for child pages
        """
        # TODO: _crawl_from parameter with fallback to self._crawl_from is confusing indirection. Just call self._crawl_from directly in callback, remove parameter.
        # Delegate link extraction, persistence and scheduling to LinkProcessor
        # Crawl callback prefers direct method but falls back to supplied callback
        pages_crawled = 0
        stopped = False
        
        def cb(link_url, next_depth):
            nonlocal pages_crawled, stopped
            if stopped:
                return
            if _crawl_from is not None:
                result = _crawl_from(link_url, next_depth, stop_event)
            else:
                result = self._crawl_from(link_url, next_depth, context, stop_event)
            pages_crawled += result[0]
            if result[1]:
                stopped = True
                
        self.link_processor.process_links(context.current_root, url, body, from_id, context, depth, crawl_callback=cb, extract_links_fn=self.extract_links)
        return (pages_crawled, stopped)
    # TODO: 9 optional parameters still high - consider config object later
    # TODO: All this "param or Default()" dependency injection is over-complex. Either: 1) require all dependencies (fail fast), 2) use single config object, or 3) accept defaults are fine and stop allowing overrides.
    # CLAUDE: configs_repo removed as requested. Consider builder pattern or CrawlerConfig dataclass when complexity grows.
    def __init__(
        self,
        pages_repo: PagesRepository,
        links_repo: LinksRepository,
        delay: Optional[float] = None,
        user_agent: Optional[str] = None,
        http_service: Optional[HttpService] = None,
        fetcher: Optional[Fetcher] = None,
        content_review_service: Optional[ContentReviewService] = None,
        robots_service: Optional[RobotsService] = None,
        link_processor: Optional[LinkProcessor] = None,
        fetch_persist_service: Optional[PageFetchPersistService] = None,
        crawl_policy: Optional[CrawlPolicy] = None,
    ):
        self.pages_repo = pages_repo
        self.links_repo = links_repo
        self.delay = delay if delay is not None else env.get_float_env("CRAWL_DELAY", 1.0)
        self.user_agent = user_agent or env.get_str_env("USER_AGENT", "InfraCrawl/0.1")
        self.http_service = http_service or HttpService(self.user_agent, http_client=requests.get)
        self.fetcher = fetcher or HttpServiceFetcher(self.http_service)
        self.content_review_service = content_review_service or ContentReviewService()
        self.robots_service = robots_service or RobotsService(self.http_service, self.user_agent)
        self.link_processor = link_processor or LinkProcessor(self.content_review_service, self.pages_repo, self.links_repo)
        self.fetch_persist_service = fetch_persist_service or PageFetchPersistService(self.http_service, self.pages_repo)
        self.crawl_policy = crawl_policy or CrawlPolicy(self.pages_repo, self.robots_service)

    # TODO: Liskov Substitution risk - fetch() is overridden in tests (see test_crawler_behavior.py) without formal contract. Subclass could return incompatible type breaking _fetch_and_store. Refactor: define IHttpFetcher protocol (fetch(url) -> tuple[int, str]); accept in __init__ instead of subclassing.
    # TODO: fetch(), _allowed_by_robots(), extract_links() are unnecessary wrapper methods. Call self.http_service.fetch() directly in _fetch_and_store, inline other wrappers.
    def fetch(self, url: str, stop_event=None):
        return self.fetcher.fetch(url, stop_event=stop_event)

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
            logger.exception("Error comparing hosts: base=%s, other=%s", base, other)
            return False

    def crawl(self, config: CrawlerConfig, stop_event=None) -> CrawlResult:
        """Crawl using the provided `CrawlerConfig` object.

        Iterates `config.root_urls` and performs depth-limited crawling from
        each root, using `config.max_depth` and other config options.
        
        Returns:
            CrawlResult with pages_crawled count and stopped flag
        """
        if config is None:
            raise ValueError("config is required for crawl")
        # Build context from the provided config
        context = CrawlContext(config)
        # Ensure max_depth is set
        if context.max_depth is None:
            context.max_depth = env.get_int_env("DEFAULT_DEPTH", 2)

        pages_crawled = 0
        stopped = False
        roots = getattr(context.config, 'root_urls', []) or []
        for ru in roots:
            # cooperative cancellation: check stop_event before starting each root
            if self._is_stopped(stop_event):
                logger.info("Crawl cancelled before starting root %s", ru)
                stopped = True
                break
            context.set_root(ru)
            result = self._crawl_from(ru, context.max_depth, context, stop_event)
            pages_crawled += result[0]
            if result[1]:  # stopped
                stopped = True
                break
        
        return CrawlResult(pages_crawled=pages_crawled, stopped=stopped)

    def _crawl_from(self, url: str, depth: int, context: CrawlContext, stop_event=None) -> tuple[int, bool]:
        """Crawl from a URL recursively up to depth.
        
        Returns:
            (pages_crawled, stopped) tuple
        """
        if context.is_visited(url):
            logger.debug("Skipping (visited) %s", url)
            return (0, False)
        context.mark_visited(url)

        from_id = self.pages_repo.ensure_page(url)

        if self._is_stopped(stop_event):
            logger.info("Crawl cancelled during traversal of %s", url)
            return (0, True)

        if self.crawl_policy.should_skip_due_to_depth(depth):
            return (0, False)
        if self.crawl_policy.should_skip_due_to_robots(url, context):
            return (0, False)
        if self.crawl_policy.should_skip_due_to_refresh(url, context):
            return (0, False)

        body = self._fetch_and_store(url, context, stop_event)
        if body is None:
            return (0, False)

        pages_crawled = 1
        stopped = False
        
        time.sleep(self.delay)
        child_result = self._process_links(url, body, from_id, context, depth, None, stop_event)
        pages_crawled += child_result[0]
        if child_result[1]:
            stopped = True
        
        return (pages_crawled, stopped)

        
