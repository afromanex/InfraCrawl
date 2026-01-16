import logging
import time
from datetime import datetime
from typing import Callable, Optional

from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.crawl_result import CrawlResult
from infracrawl.domain.http_response import HttpResponse
from infracrawl.domain.visited_tracker import VisitedTracker
from infracrawl.exceptions import HttpFetchError
from infracrawl.services.fetcher_factory import FetcherFactory
from infracrawl.services.link_processor import LinkProcessRequest

logger = logging.getLogger(__name__)

class CrawlExecutor:
    """Executes a crawl given configured collaborators.

    This class owns the crawl control-flow (traversal, cancellation checks, calling
    fetch/persist, and delegating link processing). It intentionally does NOT
    construct dependencies (that stays in the DI layer).
    """

    def __init__(
        self,
        *,
        pages_repo,
        crawl_policy,
        link_processor,
        fetch_persist_service,
        delay_seconds: float,
        fetcher_factory: FetcherFactory,
        visited_tracker_max_urls: int = 100_000,
        crawl_registry=None,
        crawl_id: Optional[str] = None,
    ):
        self.pages_repo = pages_repo
        self.crawl_policy = crawl_policy
        self.link_processor = link_processor
        self.fetch_persist_service = fetch_persist_service
        self.delay_seconds = delay_seconds
        self.fetcher_factory = fetcher_factory
        self.visited_tracker_max_urls = int(visited_tracker_max_urls)
        self.crawl_registry = crawl_registry
        self.crawl_id = crawl_id

    def _is_stopped(self, stop_event) -> bool:
        return stop_event is not None and getattr(stop_event, "is_set", lambda: False)()

    def _update_registry_progress(self, pages_fetched: int, links_found: int = 0) -> None:
        """Update the crawl registry with current progress."""
        if self.crawl_registry is not None and self.crawl_id is not None:
            try:
                self.crawl_registry.update(
                    self.crawl_id,
                    pages_fetched=pages_fetched,
                    links_found=links_found,
                )
            except Exception as e:
                logger.warning("Failed to update registry progress: %s", e)

    def fetch_and_store(self, url: str, context: CrawlContext, stop_event=None) -> Optional[str]:
        """Fetch a URL and persist the result.

        Returns the response body on success, or None on failure.
        """
        try:
            if self._is_stopped(stop_event):
                logger.info("Fetch cancelled for %s", url)
                return None
            if context is None or getattr(context, "config", None) is None:
                raise ValueError("context.config is required")
            response: HttpResponse = self.fetcher_factory.get(context.config.fetch_mode).fetch(
                url,
                stop_event=stop_event,
            )
        except HttpFetchError as e:
            logger.warning("Fetch failed for %s: %s", url, e)
            return None
        except Exception as e:
            logger.error("Fetch error for %s: %s", url, e, exc_info=True)
            return None

        fetched_at = datetime.utcnow().isoformat()
        try:
            page = self.fetch_persist_service.extract_and_persist(
                url,
                response.status_code,
                response.text,
                fetched_at,
                context=context,
            )
            logger.info(
                "Fetched %s -> status %s, page_id=%s",
                url,
                response.status_code,
                getattr(page, "page_id", None),
            )
        except Exception as e:
            logger.error("Storage error while saving %s: %s", url, e, exc_info=True)
            return None

        try:
            sc = int(response.status_code)
            if sc < 200 or sc >= 300:
                logger.warning("Non-success status for %s: %s", url, response.status_code)
        except Exception:
            logger.exception("Error parsing status code for %s: %s", url, response.status_code)

        return response.text

    def process_links(
        self,
        url: str,
        body: str,
        from_id: int,
        context: CrawlContext,
        depth: int,
        crawl_from_fn: Optional[Callable[[str, int, object], tuple[int, bool]]] = None,
        stop_event=None,
    ) -> tuple[int, bool]:
        """Extract and process links from page body.

        Returns (pages_crawled, stopped) tuple for child pages.
        """
        pages_crawled = 0
        stopped = False

        def cb(link_url, next_depth):
            nonlocal pages_crawled, stopped
            if stopped:
                return
            if crawl_from_fn is not None:
                result = crawl_from_fn(link_url, next_depth, stop_event)
            else:
                result = self.crawl_from(link_url, next_depth, context, stop_event)
            pages_crawled += result[0]
            if result[1]:
                stopped = True

        self.link_processor.process(
            LinkProcessRequest(
                current_root=context.current_root,
                base_url=url,
                html=body,
                from_id=from_id,
                context=context,
                depth=depth,
            ),
            crawl_callback=cb,
        )
        return (pages_crawled, stopped)

    def crawl(self, config, stop_event=None) -> CrawlResult:
        if config is None:
            raise ValueError("config is required for crawl")

        # Prevent unbounded memory usage on large crawls.
        context = CrawlContext(
            config,
            visited_tracker=VisitedTracker(max_size=self.visited_tracker_max_urls),
        )

        pages_crawled = 0
        stopped = False
        roots = getattr(context.config, "root_urls", []) or []
        for root_url in roots:
            if self._is_stopped(stop_event):
                logger.info("Crawl cancelled before starting root %s", root_url)
                stopped = True
                break
            context.set_root(root_url)
            result = self.crawl_from(root_url, context.max_depth, context, stop_event)
            pages_crawled += result[0]
            if result[1]:
                stopped = True
                break

        # Update registry with final page count
        self._update_registry_progress(pages_crawled)

        return CrawlResult(pages_crawled=pages_crawled, stopped=stopped)

    def crawl_from(self, url: str, depth: int, context: CrawlContext, stop_event=None) -> tuple[int, bool]:
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

        body = self.fetch_and_store(url, context, stop_event)
        if body is None:
            return (0, False)

        pages_crawled = 1
        stopped = False

        time.sleep(self.delay_seconds)
        child_result = self.process_links(url, body, from_id, context, depth, None, stop_event)
        pages_crawled += child_result[0]
        if child_result[1]:
            stopped = True

        return (pages_crawled, stopped)
