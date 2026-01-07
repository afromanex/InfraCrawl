from typing import Set, Optional
from infracrawl.domain.config import CrawlerConfig


class CrawlContext:
    def __init__(self, start_url: str, max_depth: int, config: Optional[CrawlerConfig] = None):
        self.start_url = start_url
        self.max_depth = max_depth
        self.config = config
        self.visited: Set[str] = set()


    def mark_visited(self, url: str):
        self.visited.add(url)

    def is_visited(self, url: str) -> bool:
        return url in self.visited
