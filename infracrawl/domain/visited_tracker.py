from collections import OrderedDict
from typing import Optional


class VisitedTracker:
    """
    Tracks which URLs have been visited during a crawl.
    
    Extracted from CrawlContext to follow Single Responsibility Principle.
    This class focuses solely on visited URL tracking, making it easier to:
    - Replace implementation (e.g., with bloom filter or database)
    - Test visited tracking logic independently
    - Reuse across different crawl contexts
    """
    
    def __init__(self, max_size: Optional[int] = 100_000):
        """Create a visited tracker.

        `max_size` bounds memory usage by evicting least-recently-added URLs.
        If `max_size` is None or <= 0, the tracker behaves as unbounded.
        """
        self._max_size = int(max_size) if max_size is not None else None
        if self._max_size is not None and self._max_size <= 0:
            self._max_size = None

        # OrderedDict gives us a lightweight LRU-like set.
        self._visited: "OrderedDict[str, None]" = OrderedDict()
    
    def mark(self, url: str) -> None:
        """Mark a URL as visited."""
        if url in self._visited:
            self._visited.move_to_end(url)
            return
        self._visited[url] = None
        if self._max_size is not None:
            while len(self._visited) > self._max_size:
                self._visited.popitem(last=False)
    
    def is_visited(self, url: str) -> bool:
        """Check if a URL has been visited."""
        if url in self._visited:
            self._visited.move_to_end(url)
            return True
        return False
