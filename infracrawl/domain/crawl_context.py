from typing import Set, Optional
from infracrawl.domain.config import CrawlerConfig


class CrawlContext:
    def __init__(self, config: Optional[CrawlerConfig] = None):
        # store the full config; roots and max_depth come from here
        self.config = config
        self.max_depth = config.max_depth if (config and getattr(config, 'max_depth', None) is not None) else None
        # current_root is set when iterating multiple root URLs
        self.current_root: Optional[str] = None
        # TODO: visited set grows unbounded - memory leak for large crawls
        # CLAUDE: Options: 1) LRU cache (max N URLs) 2) Bloom filter (probabilistic, small memory) 3) Database-backed (slow). For <100K URLs, set is fine.
        # TODO: No persistence - crawl cannot resume after crash
        # CLAUDE: Agreed - defer. Would need: visited URLs table, crawl_state table with resume token, queue of pending URLs.
        # TODO: QUESTION: Should visited be moved to database or use bloom filter?
        # CLAUDE: "visited" = URLs already crawled. "Bloom filter" = probabilistic data structure using <1MB for millions of URLs but 0.1% false positives. DB = persistent but slow. Current in-memory set OK for now.
        self.visited: Set[str] = set()

    def set_root(self, root: str):
        self.current_root = root

    def mark_visited(self, url: str):
        self.visited.add(url)

    def is_visited(self, url: str) -> bool:
        return url in self.visited

