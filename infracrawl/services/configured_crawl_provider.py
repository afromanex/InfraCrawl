from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable, Optional

from infracrawl.domain.crawl_session import CrawlSession
from infracrawl.domain.http_response import HttpResponse
from infracrawl.exceptions import HttpFetchError
from infracrawl.services.fetcher import Fetcher
from infracrawl.services.link_processor import LinkProcessRequest

logger = logging.getLogger(__name__)


class ConfiguredCrawlProvider:
    """Per-crawl coordinator that owns state, fetching, and traversal logic.

    Encapsulates all the crawl execution details for a single config/crawl run.
    """

    def __init__(
        self,
        fetcher: Fetcher,
        context: CrawlSession,
        pages_repo,
        crawl_policy,
        link_processor,
        fetch_persist_service,
        delay_seconds: float,
    ):
        self.fetcher = fetcher
        self.context = context
        self.pages_repo = pages_repo
        self.crawl_policy = crawl_policy
        self.link_processor = link_processor
        self.fetch_persist_service = fetch_persist_service
        self.delay_seconds = delay_seconds

    def fetch(self, url: str, stop_event=None):
        return self.fetcher.fetch(url, stop_event=stop_event)

    def is_stopped(self, stop_event) -> bool:
        return stop_event is not None and getattr(stop_event, "is_set", lambda: False)()

    def fetch_and_store(self, url: str, stop_event=None) -> Optional[str]:
        """Fetch a URL and persist the result.

        Returns the response body on success, or None on failure.
        """
        try:
            if self.is_stopped(stop_event):
                logger.info("Fetch cancelled for %s", url)
                return None
            if self.context is None or getattr(self.context, "config", None) is None:
                raise ValueError("context.config is required")
            
            response: HttpResponse = self.fetch(url, stop_event=stop_event)
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
                context=self.context,
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
        crawl_from_fn: Optional[Callable[[str, int, object], tuple[int, bool]]] = None,
        stop_event=None,
    ) -> tuple[int, bool]:
        """Extract and process links from page body.

        Returns (pages_crawled, stopped) tuple for child pages.
        """
        parent_depth = self.context.current_depth
        pages_crawled = 0
        stopped = False

        def cb(link_url, next_depth):
            nonlocal pages_crawled, stopped
            if stopped:
                return
            # Determine remaining depth budget for the child.
            child_depth = parent_depth - 1 if parent_depth is not None else None
            if child_depth is not None and child_depth < 0:
                return
            prev_depth = self.context.current_depth
            self.context.set_current_depth(child_depth)
            if crawl_from_fn is not None:
                result = crawl_from_fn(link_url, next_depth, stop_event)
            else:
                result = self.crawl_from(link_url, stop_event)
            self.context.set_current_depth(prev_depth)
            pages_crawled += result[0]
            if result[1]:
                stopped = True

        self.link_processor.process(
            LinkProcessRequest(
                current_root=self.context.current_root,
                base_url=url,
                html=body,
                from_id=from_id,
                context=self.context,
                depth=parent_depth,
            ),
            crawl_callback=cb,
        )
        return (pages_crawled, stopped)

    def crawl_from(self, url: str, stop_event=None) -> tuple[int, bool]:
        """Crawl a single URL and its children.

        Returns (pages_crawled, stopped) tuple.
        """
        depth = self.context.current_depth
        if self.context.is_visited(url):
            logger.debug("Skipping (visited) %s", url)
            return (0, False)
        self.context.mark_visited(url)

        from_id = self.pages_repo.ensure_page(url)

        if self.is_stopped(stop_event):
            logger.info("Crawl cancelled during traversal of %s", url)
            return (0, True)

        if depth is not None and self.crawl_policy.should_skip_due_to_depth(depth):
            return (0, False)
        if self.crawl_policy.should_skip_due_to_robots(url, self.context):
            return (0, False)
        if self.crawl_policy.should_skip_due_to_refresh(url, self.context):
            return (0, False)

        body = self.fetch_and_store(url, stop_event)
        if body is None:
            return (0, False)

        self.context.increment_pages_crawled(1)
        pages_crawled = 1
        stopped = False

        time.sleep(self.delay_seconds)
        child_result = self.process_links(url, body, from_id, None, stop_event)
        if child_result[0]:
            self.context.increment_pages_crawled(child_result[0])
        pages_crawled += child_result[0]
        if child_result[1]:
            stopped = True

        return (pages_crawled, stopped)