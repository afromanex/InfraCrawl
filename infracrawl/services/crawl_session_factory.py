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
        
        If a registry is configured, the session will be registered for tracking
        and will receive a crawl_id and stop_event for cancellation support.
        
        Args:
            config: The crawler configuration for this session
            
        Returns:
            A fully configured CrawlSession ready to start crawling
        """
        crawl_id = None
        stop_event = None
        
        # Register with tracking system if available
        if self.registry is not None:
            handle = self.registry.start(
                config_name=config.config_path,
                config_id=config.config_id,
            )
            crawl_id = handle.crawl_id
            stop_event = handle.stop_event
        
        # Create session with tracking details
        session = CrawlSession(
            config=config,
            visited_tracker=VisitedTracker(max_size=self.visited_tracker_max_urls),
            crawl_id=crawl_id,
            stop_event=stop_event,
        )
        
        return session
