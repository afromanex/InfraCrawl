import threading
from contextlib import contextmanager
from typing import Optional
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.visited_tracker import VisitedTracker


class CrawlSession:
    """
    Full lifecycle tracking for a single crawl execution.
    
    Represents a crawl session from start to finish, including configuration,
    execution state, progress tracking, and cancellation mechanisms.
    
    The session can optionally integrate with a crawl registry for real-time
    observability and cancellation support.
    """
    
    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        visited_tracker: Optional[VisitedTracker] = None,
        crawl_id: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
        registry=None,
    ):
        # Identity & tracking
        self.crawl_id = crawl_id
        self.stop_event = stop_event if stop_event is not None else threading.Event()
        self._registry = registry
        
        # Configuration
        self.config = config
        
        # Execution state - current_root is set when iterating multiple root URLs
        self.current_root: Optional[str] = None
        # Visited URL tracking delegated to separate class (SRP fix)
        self.visited_tracker = visited_tracker if visited_tracker is not None else VisitedTracker()
        # Track pages fetched within the current crawl
        self.pages_crawled: int = 0

    def start_tracking(self) -> None:
        """Begin registry tracking if registry is configured.
        
        Calls registry.start() to create a tracking record and obtain
        a crawl_id and stop_event for cancellation support.
        """
        if self._registry is not None:
            handle = self._registry.start(
                config_name=self.config.config_path if self.config else None,
                config_id=self.config.config_id if self.config else None,
            )
            self.crawl_id = handle.crawl_id
            self.stop_event = handle.stop_event

    def update_progress(self) -> None:
        """Report current progress to registry if tracking is active."""
        if self._registry is not None and self.crawl_id is not None:
            self._registry.update(
                self.crawl_id,
                pages_fetched=self.pages_crawled,
            )

    def finish_tracking(self, status: str = "finished", error: Optional[str] = None) -> None:
        """Complete registry tracking if active.
        
        Marks the crawl as finished/failed and cleans up cancellation resources.
        
        Args:
            status: Final status ("finished", "failed", "cancelled")
            error: Optional error message if status is "failed"
        """
        if self._registry is not None and self.crawl_id is not None:
            self._registry.finish(
                self.crawl_id,
                status=status,
                error=error,
            )

    def increment_pages_crawled(self, count: int = 1) -> None:
        self.pages_crawled += int(count)

    def set_current_page(self, page):
        """Set the page currently being processed for link extraction."""
        self.current_root = page.page_url

    def mark_visited(self, page):
        """Delegate to visited tracker."""
        self.visited_tracker.mark(page.page_url)

    def is_visited(self, page) -> bool:
        """Delegate to visited tracker."""
        return self.visited_tracker.is_visited(page.page_url)

    def is_stopped(self) -> bool:
        """Check if crawling has stopped."""
        return self.stop_event.is_set()

    def mark_stopped(self) -> None:
        """Mark that crawling should stop."""
        self.stop_event.set()

