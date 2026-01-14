from typing import Optional
from urllib.robotparser import RobotFileParser


class RobotsCache:
    """
    Cache for RobotFileParser instances keyed by domain base URL.
    
    Extracted from RobotsService to follow Single Responsibility Principle.
    This class focuses solely on caching, making it easier to:
    - Add TTL expiration logic
    - Implement LRU eviction (max cache size)
    - Add cache metrics (hit rate, evictions)
    - Test cache behavior independently
    """
    
    def __init__(self):
        # TODO: Unbounded cache - memory leak for crawling many domains
        # TODO: No TTL - stale robots.txt cached forever
        # Future: Use cachetools.TTLCache or LRUCache
        self._cache: dict[str, Optional[RobotFileParser]] = {}
    
    def get(self, base_url: str) -> Optional[RobotFileParser]:
        """Get cached parser for a domain, or None if not cached."""
        return self._cache.get(base_url)
    
    def set(self, base_url: str, parser: Optional[RobotFileParser]) -> None:
        """Cache a parser for a domain. None indicates fetch failed."""
        self._cache[base_url] = parser
    
    def clear(self) -> None:
        """Clear entire cache. Useful for testing or manual cache invalidation."""
        self._cache.clear()
