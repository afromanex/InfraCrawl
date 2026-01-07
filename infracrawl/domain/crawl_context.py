from typing import Set, Optional
from infracrawl.domain.config import CrawlerConfig


class CrawlContext:
    def __init__(self, config: Optional[CrawlerConfig] = None):
        # store the full config; roots and max_depth come from here
        self.config = config
        self.max_depth = config.max_depth if (config and getattr(config, 'max_depth', None) is not None) else None
        # current_root is set when iterating multiple root URLs
        self.current_root: Optional[str] = None
        self.visited: Set[str] = set()

    def set_root(self, root: str):
        self.current_root = root

    def mark_visited(self, url: str):
        self.visited.add(url)

    def is_visited(self, url: str) -> bool:
        return url in self.visited

