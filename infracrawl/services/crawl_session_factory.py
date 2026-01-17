"""Factory for creating CrawlSession instances."""
from typing import Optional
from infracrawl.domain import CrawlSession
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.visited_tracker import VisitedTracker


class CrawlSessionFactory:
    """Creates configured CrawlSession instances with optional registry tracking."""
    
    def __init__(
        self,
        *,
        registry=None,
        visited_tracker_max_urls: int = 100_000,
    ):
        """Initialize factory.
        
        Args:
            registry: Optional crawl registry for tracking/cancellation (InMemoryCrawlRegistry)
            visited_tracker_max_urls: Maximum URLs to track as visited per session
        """
        self.registry = registry
        self.visited_tracker_max_urls = int(visited_tracker_max_urls)
    
    def create(self, config: CrawlerConfig) -> CrawlSession:
        """Create a new crawl session for the given config.
        
        If a registry is configured, the session will automatically begin tracking
        and will have a crawl_id and stop_event for cancellation support.
        
        Args:
            config: The crawler configuration for this session
            
        Returns:
            A fully configured CrawlSession, already tracking if registry exists
        """
        # Create session with registry reference (tracking not started yet)
        session = CrawlSession(
            config=config,
            visited_tracker=VisitedTracker(max_size=self.visited_tracker_max_urls),
            registry=self.registry,
        )
        
        # Start tracking immediately if registry is available
        # This makes the session "hot" - ready to be used with tracking active
        session.start_tracking()
        
        return session
