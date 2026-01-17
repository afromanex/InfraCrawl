from __future__ import annotations

from typing import Iterable, Optional

from infracrawl.domain import Link


class LinkPersister:
    """Persists discovered links using repositories.

    This is intentionally separate from link extraction and crawl scheduling.
    """

    def __init__(self, pages_repo, links_repo):
        self.pages_repo = pages_repo
        self.links_repo = links_repo

    def persist_links(self, *, from_id: int, links: Iterable[tuple[str, str]], from_depth: Optional[int] = None, config_id: Optional[int] = None) -> None:
        """Persist a batch of (url, anchor_text) links from a given page id.
        
        Args:
            from_id: The page_id that the links were discovered from
            links: Iterable of (url, anchor_text) tuples
            from_depth: The depth of the source page (discovered links will be at from_depth + 1)
            config_id: The config ID for the discovered pages
        """
        # Materialize once because we need to iterate multiple times.
        links_list = list(links)
        if not links_list:
            return

        link_urls = [url for url, _ in links_list]
        # Pass next depth level when discovering new pages
        next_depth = from_depth + 1 if from_depth is not None else None
        url_to_id = self.pages_repo.ensure_pages_batch(link_urls, discovered_depth=next_depth, config_id=config_id)
        link_objects = [
            Link(link_id=None, link_from_id=from_id, link_to_id=url_to_id[link_url], anchor_text=anchor)
            for link_url, anchor in links_list
        ]

        self.links_repo.insert_links_batch(link_objects)
