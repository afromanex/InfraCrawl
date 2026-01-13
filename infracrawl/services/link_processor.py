import logging
from urllib.parse import urlparse

from infracrawl.domain import Link

logger = logging.getLogger(__name__)


class LinkProcessor:
    def __init__(self, content_review_service, pages_repo, links_repo):
        self.content_review_service = content_review_service
        self.pages_repo = pages_repo
        self.links_repo = links_repo

    def _same_host(self, base: str, other: str) -> bool:
        try:
            b = urlparse(base).hostname
            o = urlparse(other).hostname
            return b == o or (b and o and o.endswith('.' + b))
        except Exception:
            logger.exception("Error comparing hosts: base=%s, other=%s", base, other)
            return False

    def process_links(self, current_root: str, base_url: str, html: str, from_id: int, context, depth: int, crawl_callback=None, extract_links_fn=None):
        """Extract links from `html` and persist them; schedule further crawling via `crawl_callback`.

        - `current_root` is the root URL for host filtering.
        - `crawl_callback(link_url, next_depth)` is invoked for links to be crawled (if provided).
        """
        # Allow caller to supply an extract_links function (useful for testing/mocking)
        if extract_links_fn is None:
            links = self.content_review_service.extract_links(base_url, html)
        else:
            links = extract_links_fn(base_url, html)
        for link_url, anchor in links:
            if not self._same_host(current_root, link_url):
                logger.debug("Skipping (external) %s -> not same host as %s", link_url, current_root)
                continue
            to_id = self.pages_repo.ensure_page(link_url)
            link_obj = Link(link_id=None, link_from_id=from_id, link_to_id=to_id, anchor_text=anchor)
            self.links_repo.insert_link(link_obj)
            if depth - 1 >= 0:
                if crawl_callback is not None:
                    crawl_callback(link_url, depth - 1)
