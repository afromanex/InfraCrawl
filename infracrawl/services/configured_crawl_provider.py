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

    def fetch_and_persist(self, page: Page) -> bool:
        """Fetch a URL, persist the page, and mutate page in-place.
        
        Mutates: page.page_content, page.plain_text, page.filtered_plain_text, 
                 page.content_hash, page.page_id, page.http_status, page.fetched_at
        Returns: True on success, False on failure
        """
        url = page.page_url
        try:
            if self.context.is_stopped():
                logger.info("Fetch cancelled for %s", url)
                return False
            if self.context.config is None:
                raise ValueError("context.config is required")
            
            response: HttpResponse = self.fetcher.fetch(url, stop_event=self.context.stop_event)
        except HttpFetchError as e:
            logger.warning("Fetch failed for %s: %s", url, e)
            return False
        except Exception as e:
            logger.error("Fetch error for %s: %s", url, e, exc_info=True)
            return False

        # Skip unsupported content types
        if not self.fetch_persist_service.should_persist(response, url):
            return False

        # Mutate page with fetch results
        page.page_content = response.text
        page.http_status = response.status_code
        page.fetched_at = datetime.utcnow()
        page.config_id = self.context.config.config_id

        # Extract text and persist (mutates page with plain_text, filtered_plain_text, content_hash, page_id)
        success = self.fetch_persist_service.extract_and_persist(page)
        if not success:
            logger.error("Failed to extract and persist %s", url)
            return False

        logger.info(
            "Fetched %s -> status %s, page_id=%s",
            url,
            page.http_status,
            page.page_id,
        )

        if page.http_status < 200 or page.http_status >= 300:
            logger.warning("Non-success status for %s: %s", url, page.http_status)

        return True

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
            return False  # Max depth reached, not a stop signal
        
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

    def _should_fetch_page(self, page: Page, depth: Optional[int]) -> tuple[bool, str]:
        """Determine if a page should be fetched.
        
        Returns:
            (should_fetch, reason) tuple where reason explains why not to fetch
        """
        url = page.page_url
        
        if self.context.is_visited(page):
            return False, "already visited"
        
        if depth is not None and depth < 0:
            return False, "max depth reached"
        
        if self.crawl_policy.should_skip_due_to_robots(url, self.context):
            return False, "blocked by robots.txt"
        
        if self.crawl_policy.should_skip_due_to_refresh(url, self.context):
            return False, "refresh policy"
        
        return True, ""

    def fetch_page(self, page: Page) -> bool:
        """Fetch and persist a single page.
        
        Args:
            page: Page to fetch (will be enriched with content)
            
        Returns:
            True if successful, False otherwise
        """
        url = page.page_url
        
        # Enrich page with database record
        self.pages_repo.ensure_page(page)
        
        if self.context.is_stopped():
            logger.info("Fetch cancelled for %s", url)
            return False
        
        # Fetch and persist
        success = self.fetch_and_persist(page)
        if not success:
            return False
        
        self.context.increment_pages_crawled(1)
        time.sleep(self.context.config.delay_seconds)
        
        return True

    def crawl_from(self, page: Page, depth: Optional[int]) -> bool:
        """Crawl a single page and its children.

        The page object is enriched as we go (page_id, page_content).
        Recursively processes children at depth-1 until depth limit is reached.
        
        Args:
            page: Page to crawl
            depth: Current depth budget (None for unlimited)
            
        Returns:
            True if crawl was cancelled, False otherwise.
        """
        url = page.page_url
        
        # Set current page for link extraction and push to registry immediately
        self.context.set_current_page(page)
        self.context.update_progress()
        
        # Check if we should fetch this page
        should_fetch, reason = self._should_fetch_page(page, depth)
        if not should_fetch:
            logger.debug("Skipping (%s) %s", reason, url)
            return False
        
        self.context.mark_visited(page)
        
        # Fetch the page
        if not self.fetch_page(page):
            return False
        
        # Process links and recurse
        was_cancelled = self.process_links(page, depth)
        
        return was_cancelled
    
    def crawl_children_from(self, page: Page, depth: Optional[int]) -> bool:
        """Process children of an already-fetched page.
        
        Used for resuming crawls where the page was already fetched but we need
        to continue crawling its children.
        
        Args:
            page: Page that was already fetched
            depth: Current depth budget (None for unlimited)
            
        Returns:
            True if crawl was cancelled, False otherwise
        """
        url = page.page_url
        
        # Set current page for link extraction and push to registry immediately
        self.context.set_current_page(page)
        self.context.update_progress()
        
        # Mark as visited to prevent re-crawling
        self.context.mark_visited(page)
        
        # Ensure page exists in DB (should already exist for resume case)
        self.pages_repo.ensure_page(page)
        
        # Load page content from database if not already in memory
        if page.page_content is None:
            existing_page = self.pages_repo.get_page_by_url(url)
            if existing_page:
                page.page_content = existing_page.page_content
            else:
                logger.warning("Could not load page content for resume of %s", url)
                return False
        
        if self.context.is_stopped():
            logger.info("Crawl cancelled during traversal of %s", url)
            return True
        
        logger.debug("Processing children of already-visited %s", url)
        
        # Process links without fetching
        was_cancelled = self.process_links(page, depth)

        return was_cancelled