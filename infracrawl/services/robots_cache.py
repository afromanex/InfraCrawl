import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional
from urllib.robotparser import RobotFileParser


@dataclass(frozen=True)
class _RobotsCacheEntry:
    parser: Optional[RobotFileParser]
    stored_at: float


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
    
    def __init__(self, *, max_size: int = 2048, ttl_seconds: int = 3600):
        """Create a robots.txt cache.

        - `max_size` bounds the number of domains cached (LRU eviction).
        - `ttl_seconds` bounds staleness; entries older than TTL are treated as missing.
        """
        self._max_size = int(max_size) if max_size is not None else 2048
        if self._max_size <= 0:
            self._max_size = 1

        self._ttl_seconds = int(ttl_seconds) if ttl_seconds is not None else 3600
        if self._ttl_seconds <= 0:
            # Treat non-positive TTL as "don't cache" by expiring immediately.
            self._ttl_seconds = 0

        self._cache: "OrderedDict[str, _RobotsCacheEntry]" = OrderedDict()

    def _is_expired(self, entry: _RobotsCacheEntry) -> bool:
        if self._ttl_seconds == 0:
            return True
        return (time.time() - entry.stored_at) > self._ttl_seconds

    def _evict_if_needed(self) -> None:
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
    
    def get(self, base_url: str) -> Optional[RobotFileParser]:
        """Get cached parser for a domain, or None if not cached."""
        entry = self._cache.get(base_url)
        if entry is None:
            return None
        if self._is_expired(entry):
            try:
                del self._cache[base_url]
            except KeyError:
                pass
            return None
        # Refresh LRU order on hit
        self._cache.move_to_end(base_url)
        return entry.parser
    
    def set(self, base_url: str, parser: Optional[RobotFileParser]) -> None:
        """Cache a parser for a domain. None indicates fetch failed."""
        self._cache[base_url] = _RobotsCacheEntry(parser=parser, stored_at=time.time())
        self._cache.move_to_end(base_url)
        self._evict_if_needed()
    
    def clear(self) -> None:
        """Clear entire cache. Useful for testing or manual cache invalidation."""
        self._cache.clear()
