import logging
from typing import Callable, Optional
from urllib.parse import urlparse

from infracrawl.services.link_persister import LinkPersister
from infracrawl.domain.crawl_session import CrawlSession
from infracrawl.domain.page import Page

logger = logging.getLogger(__name__)


class LinkProcessor:
    def __init__(self, content_review_service, link_persister: LinkPersister):
        self.content_review_service = content_review_service
        self.link_persister = link_persister

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

    def process(self, page: Page, context: CrawlSession, *, crawl_child_page: Optional[Callable[[Page], None]] = None) -> None:
        """Extract links from the page and persist them.

        Links are stored in the database with NULL content (discovered but not yet fetched).
        They are stored at depth+1 relative to the current page.
        They will be crawled in subsequent iterations at the next depth level.
        
        Note: crawl_child_page callback is ignored in iterative crawling mode.
        """
        links = self.content_review_service.extract_links(page.page_url, page.page_content)
        
        # Filter to same-host links only
        same_host_links = []
        for link_url, anchor in links:
            if not self._same_host(context.current_root, link_url):
                logger.debug("Skipping (external) %s -> not same host as %s", link_url, context.current_root)
                continue
            same_host_links.append((link_url, anchor))
        
        if not same_host_links:
            logger.debug("No same-host links found on %s", page.page_url)
            return

        # Persist links (batch DB work) - these will be discovered but not yet fetched
        # Pass depth so discovered pages can be marked at next depth level
        self.link_persister.persist_links(
            from_id=page.page_id, 
            links=same_host_links,
            from_depth=page.discovered_depth,
            config_id=page.config_id
        )
        
        # Update session stats
        context.links_discovered += len(same_host_links)
        
        logger.info("Persisted %d links from %s at depth %s (will be crawled at depth %s)", 
                   len(same_host_links), page.page_url, page.discovered_depth, (page.discovered_depth + 1) if page.discovered_depth is not None else "?")


