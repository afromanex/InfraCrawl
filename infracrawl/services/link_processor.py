import logging
from typing import Callable, Optional
from urllib.parse import urlparse

from infracrawl.domain import Link
from infracrawl.domain.crawl_context import CrawlContext

logger = logging.getLogger(__name__)

# TODO: SRP - LinkProcessor does 3 jobs: (1) calls content_review_service.extract_links (2) persists links via links_repo (3) schedules crawls via callback. Concrete risk: changing link storage (batch inserts) requires editing crawl scheduling logic. Minimal fix: extract LinkPersister class with persist(from_id, to_id, anchor); processor focuses on orchestration.
class LinkProcessor:
    def __init__(self, content_review_service, pages_repo, links_repo):
        self.content_review_service = content_review_service
        self.pages_repo = pages_repo
        self.links_repo = links_repo

    def _same_host(self, base: str, other: str) -> bool:
        try:
            b = urlparse(base).hostname
            o = urlparse(other).hostname
            # CLAUDE: Subdomains same-host is correct for most crawlers. Example: www.example.com and blog.example.com are same site.
            return b == o or (b and o and o.endswith('.' + b))
        except Exception:
            logger.exception("Error comparing hosts: base=%s, other=%s", base, other)
            # CLAUDE: Returning False treats parse errors as external links - conservative and safe.
            return False

    # TODO: 8 parameters - refactor later with CrawlState object
    # CLAUDE: Acknowledged - defer until pattern emerges
    def process_links(self, current_root: str, base_url: str, html: str, from_id: int, context: CrawlContext, depth: int, crawl_callback: Optional[Callable[[str, int], None]] = None, extract_links_fn: Optional[Callable[[str, str], list]] = None):
        """Extract links from `html` and persist them; schedule further crawling via `crawl_callback`.

        - `current_root` is the root URL for host filtering.
        - `crawl_callback(link_url, next_depth)` is invoked for links to be crawled (if provided).
        """
        # TODO: Optional extract_links_fn parameter is over-engineering for testing. Tests should mock content_review_service.extract_links instead of passing function parameter.
        # Allow caller to supply an extract_links function (useful for testing/mocking)
        if extract_links_fn is None:
            links = self.content_review_service.extract_links(base_url, html)
        else:
            links = extract_links_fn(base_url, html)
        
        # Filter to same-host links only
        same_host_links = []
        for link_url, anchor in links:
            if not self._same_host(current_root, link_url):
                logger.debug("Skipping (external) %s -> not same host as %s", link_url, current_root)
                continue
            same_host_links.append((link_url, anchor))
        
        if not same_host_links:
            return
        
        # Batch ensure all pages (single DB query)
        link_urls = [url for url, _ in same_host_links]
        url_to_id = self.pages_repo.ensure_pages_batch(link_urls)
        
        # Create link objects for batch insert
        # TODO: Link domain object expects link_id: int but gets None
        # CLAUDE: Domain model should use Optional[int] for link_id since repo assigns it. Low priority fix.
        link_objects = [
            Link(link_id=None, link_from_id=from_id, link_to_id=url_to_id[link_url], anchor_text=anchor)
            for link_url, anchor in same_host_links
        ]
        
        # Batch insert all links (single DB transaction)
        self.links_repo.insert_links_batch(link_objects)
        
        # Schedule crawls for next depth
        if depth - 1 >= 0 and crawl_callback is not None:
            for link_url, _ in same_host_links:
                crawl_callback(link_url, depth - 1)
