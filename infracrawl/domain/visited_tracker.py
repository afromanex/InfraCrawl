from typing import Set


class VisitedTracker:
    """
    Tracks which URLs have been visited during a crawl.
    
    Extracted from CrawlContext to follow Single Responsibility Principle.
    This class focuses solely on visited URL tracking, making it easier to:
    - Replace implementation (e.g., with bloom filter or database)
    - Test visited tracking logic independently
    - Reuse across different crawl contexts
    """
    
    def __init__(self):
        # TODO: visited set grows unbounded - memory leak for large crawls
        # CLAUDE: Options: 1) LRU cache (max N URLs) 2) Bloom filter (probabilistic, small memory) 3) Database-backed (slow). For <100K URLs, set is fine.
        # TODO: No persistence - crawl cannot resume after crash
        # CLAUDE: Agreed - defer. Would need: visited URLs table, crawl_state table with resume token, queue of pending URLs.
        # TODO: QUESTION: Should visited be moved to database or use bloom filter?
        # CLAUDE: "visited" = URLs already crawled. "Bloom filter" = probabilistic data structure using <1MB for millions of URLs but 0.1% false positives. DB = persistent but slow. Current in-memory set OK for now.
        self._visited: Set[str] = set()
    
    def mark(self, url: str) -> None:
        """Mark a URL as visited."""
        self._visited.add(url)
    
    def is_visited(self, url: str) -> bool:
        """Check if a URL has been visited."""
        return url in self._visited
