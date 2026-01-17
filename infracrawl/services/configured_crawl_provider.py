from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable, Optional

from infracrawl.domain.crawl_session import CrawlSession
from infracrawl.domain.http_response import HttpResponse
from infracrawl.domain.page import Page
from infracrawl.exceptions import HttpFetchError
from infracrawl.services.fetcher import Fetcher

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
    ):
        self.fetcher = fetcher
        self.context = context
        self.pages_repo = pages_repo
        self.crawl_policy = crawl_policy
        self.link_processor = link_processor
        self.fetch_persist_service = fetch_persist_service

    def fetch(self, url: str, stop_event=None):
        return self.fetcher.fetch(url, stop_event=stop_event)

    def fetch_and_store(self, url: str, stop_event=None) -> Optional[str]:
        """Fetch a URL and persist the result.

        Returns the response body on success, or None on failure.
        """
        try:
            if self.context.is_stopped():
                logger.info("Fetch cancelled for %s", url)
                return None
            if self.context.config is None:
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
        page: Page,
        depth: Optional[int],
    ) -> bool:
        """Extract and process links from page body.

        Returns stopped status.
        """
        # Calculate depth for children
        child_depth = depth - 1 if depth is not None else None
        crawl_depth_reached = child_depth is not None and child_depth < 0
        if crawl_depth_reached:
            return self.context.is_stopped()
        
        def crawl_child_page(child_page):
            # Check if already stopped
            if self.context.is_stopped():
                logger.debug("Skipping child (already stopped) %s", child_page.page_url)
                return
            
            # Crawl the child
            child_stopped = self.crawl_from(child_page, child_depth)
            
            # If this crawl detected stop, signal remaining siblings to skip
            if child_stopped:
                logger.debug("Stop detected during child crawl, skipping remaining siblings: %s", child_page.page_url)
                self.context.mark_stopped()

        self.link_processor.process(page, self.context, crawl_child_page=crawl_child_page)
        return self.context.is_stopped()

    def crawl_from(self, page: Page, depth: Optional[int]) -> bool:
        """Crawl a single page and its children.

        The page object is enriched as we go (page_id, page_content).
        Recursively processes children at depth-1 until depth limit is reached.
        
        Args:
            page: Page to crawl
            depth: Current depth budget (None for unlimited)
            
        Returns:
            stopped status.
        """
        url = page.page_url
        
        # Set up root for link extraction
        self.context.set_root(url)
        
        if self.context.is_visited(url):
            logger.debug("Skipping (visited) %s", url)
            return False
        self.context.mark_visited(url)

        # Enrich page with database record
        page.page_id = self.pages_repo.ensure_page(url)

        if self.context.is_stopped():
            logger.info("Crawl cancelled during traversal of %s", url)
            return True

        if depth is not None and depth < 0:
            logger.debug("Skipping (max depth reached) %s", url)
            return False
        if self.crawl_policy.should_skip_due_to_robots(url, self.context):
            return False
        if self.crawl_policy.should_skip_due_to_refresh(url, self.context):
            return False

        # Fetch and enrich page with content
        body = self.fetch_and_store(url, self.context.stop_event)
        if body is None:
            return False

        page.page_content = body
        self.context.increment_pages_crawled(1)

        time.sleep(self.context.config.delay_seconds)
        stopped = self.process_links(page, depth)

        return stopped