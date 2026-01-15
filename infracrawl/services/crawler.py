import logging
from typing import Optional

import requests

from infracrawl.services.http_service import HttpService
from infracrawl.services.fetcher import Fetcher, HttpServiceFetcher
from infracrawl.services.fetcher_factory import FetcherFactory, DisabledHeadlessFetcher
from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.services.content_review_service import ContentReviewService
from infracrawl.services.robots_service import RobotsService
from infracrawl.services.link_processor import LinkProcessor
from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.services.crawl_policy import CrawlPolicy

from infracrawl import config as env
from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.crawl_result import CrawlResult

logger = logging.getLogger(__name__)

# TODO: Single Responsibility violation - Crawler orchestrates crawling, enforces robots.txt, manages depth, handles refresh logic, extracts links, persists pages. Risk: any change to one concern (e.g., robots policy) requires modifying Crawler. Refactor: extract CrawlOrchestrator as thin coordinator; push depth/robots/refresh checks into separate policy objects.
# RESPONSE: We can extract to RobotsTxtService, but for simplicity we will keep it as is for now.
class Crawler:
    def _is_stopped(self, stop_event) -> bool:
        return self._executor._is_stopped(stop_event)

    def _fetch_and_store(self, url: str, context, stop_event=None):
        return self._executor.fetch_and_store(url, context, stop_event)

    def _process_links(self, url: str, body: str, from_id: int, context, depth: int, _crawl_from=None, stop_event=None) -> tuple[int, bool]:
        # Preserve the legacy signature used internally/tests.
        return self._executor.process_links(url, body, from_id, context, depth, _crawl_from, stop_event)
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
        headless_fetcher: Optional[Fetcher] = None,
        fetcher_factory: Optional[FetcherFactory] = None,
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
        self.headless_fetcher = headless_fetcher
        self.fetcher_factory = fetcher_factory or FetcherFactory(
            http_fetcher=self.fetcher,
            headless_fetcher=self.headless_fetcher or DisabledHeadlessFetcher(),
        )
        self.content_review_service = content_review_service or ContentReviewService()
        self.robots_service = robots_service or RobotsService(self.http_service, self.user_agent)
        self.link_processor = link_processor or LinkProcessor(self.content_review_service, self.pages_repo, self.links_repo)
        self.fetch_persist_service = fetch_persist_service or PageFetchPersistService(self.http_service, self.pages_repo)
        self.crawl_policy = crawl_policy or CrawlPolicy(self.pages_repo, self.robots_service)

        self._executor = CrawlExecutor(
            pages_repo=self.pages_repo,
            crawl_policy=self.crawl_policy,
            link_processor=self.link_processor,
            fetch_persist_service=self.fetch_persist_service,
            delay_seconds=self.delay,
            fetch_fn=lambda url, stop_event, fetch_mode: self.fetch(url, stop_event=stop_event, fetch_mode=fetch_mode),
            extract_links_fn=lambda base_url, html: self.extract_links(base_url, html),
        )

    # TODO: Liskov Substitution risk - fetch() is overridden in tests (see test_crawler_behavior.py) without formal contract. Subclass could return incompatible type breaking _fetch_and_store. Refactor: define IHttpFetcher protocol (fetch(url) -> tuple[int, str]); accept in __init__ instead of subclassing.
    # TODO: fetch(), _allowed_by_robots(), extract_links() are unnecessary wrapper methods. Call self.http_service.fetch() directly in _fetch_and_store, inline other wrappers.
    def fetch(self, url: str, stop_event=None, fetch_mode: str = None):
        chosen = self.fetcher_factory.get(fetch_mode)
        return chosen.fetch(url, stop_event=stop_event)

    def _allowed_by_robots(self, url: str, robots_enabled: bool) -> bool:
        return self.robots_service.allowed_by_robots(url, robots_enabled)

    def extract_links(self, base_url: str, html: str):
        return self.content_review_service.extract_links(base_url, html)

    def crawl(self, config: CrawlerConfig, stop_event=None) -> CrawlResult:
        return self._executor.crawl(config, stop_event)

    def _crawl_from(self, url: str, depth: int, context: CrawlContext, stop_event=None) -> tuple[int, bool]:
        return self._executor.crawl_from(url, depth, context, stop_event)

        
