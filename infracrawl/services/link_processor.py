import logging
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import urlparse

from infracrawl.services.link_persister import LinkPersister
from infracrawl.domain.crawl_session import CrawlSession
from infracrawl.domain.page import Page

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LinkProcessRequest:
    page: Page
    context: CrawlSession


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

    def process(self, req: LinkProcessRequest, *, crawl_callback: Optional[Callable[[str], None]] = None) -> None:
        """Extract links from the page, persist them, and optionally schedule crawls.

        `crawl_callback(link_url)` is invoked for links to be crawled.
        """
        links = self.content_review_service.extract_links(req.page.page_url, req.page.page_content)
        
        # Filter to same-host links only
        same_host_links = []
        for link_url, anchor in links:
            if not self._same_host(req.context.current_root, link_url):
                logger.debug("Skipping (external) %s -> not same host as %s", link_url, req.context.current_root)
                continue
            same_host_links.append((link_url, anchor))
        
        if not same_host_links:
            return

        # Persist links (batch DB work)
        self.link_persister.persist_links(from_id=req.page.page_id, links=same_host_links)
        
        # Schedule crawls for next depth
        if req.context.current_depth - 1 >= 0 and crawl_callback is not None:
            for link_url, _ in same_host_links:
                crawl_callback(link_url)
