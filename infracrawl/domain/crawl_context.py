from typing import Optional
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.visited_tracker import VisitedTracker


class CrawlContext:
    """
    Crawl execution context that holds configuration and tracks crawl state.
    
    Note: Still manages 2 responsibilities - config holder and current_root iteration.
    Further refactoring could split this, but the improvement-to-effort ratio is low.
    """
    
    def __init__(self, config: Optional[CrawlerConfig] = None, visited_tracker: Optional[VisitedTracker] = None):
        # store the full config; roots and max_depth come from here
        self.config = config
        # TODO: Complex defensive code - getattr(config, 'max_depth', None) is not None. If config exists, max_depth should always exist. Simplify: self.max_depth = config.max_depth if config else None
        self.max_depth = config.max_depth if (config and getattr(config, 'max_depth', None) is not None) else None
        # current_root is set when iterating multiple root URLs
        self.current_root: Optional[str] = None
        # Visited URL tracking delegated to separate class (SRP fix)
        self.visited_tracker = visited_tracker if visited_tracker is not None else VisitedTracker()

    def set_root(self, root: str):
        self.current_root = root

    def mark_visited(self, url: str):
        """Delegate to visited tracker."""
        self.visited_tracker.mark(url)

    def is_visited(self, url: str) -> bool:
        """Delegate to visited tracker."""
        return self.visited_tracker.is_visited(url)

