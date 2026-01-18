"""Factory for rebuilding CrawlSession instances from incomplete crawls."""
from typing import Optional
import logging
from infracrawl.domain import CrawlSession
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.visited_tracker import VisitedTracker
from infracrawl.repository.pages import PagesRepository

logger = logging.getLogger(__name__)


class CrawlSessionResumeFactory:
    """Rebuilds CrawlSession instances for resuming incomplete crawls.
    
    This factory is specifically for resume operations and requires access
    to the pages repository to load previously-visited URLs.
    """
    
    def __init__(
        self,
        *,
        pages_repo: PagesRepository,
        links_repo=None,
        registry=None,
        visited_tracker_max_urls: int = 100_000,
    ):
        """Initialize resume factory.
        
        Args:
            pages_repo: Repository for loading visited URLs from database
            links_repo: Optional repository for loading link counts
            registry: Optional crawl registry for tracking/cancellation
            visited_tracker_max_urls: Maximum URLs to track as visited per session
        """
        self.pages_repo = pages_repo
        self.links_repo = links_repo
        self.registry = registry
        self.visited_tracker_max_urls = int(visited_tracker_max_urls)
    
    def rebuild(self, config: CrawlerConfig) -> CrawlSession:
        """Rebuild a crawl session for resuming from a previous incomplete run.
        
        Loads all previously-visited URLs from the database and pre-populates
        the visited tracker so the crawler will skip already-crawled pages.
        
        Args:
            config: The crawler configuration for this session
            
        Returns:
            A CrawlSession with pre-populated visited tracker, ready to resume
        """
        # Load previously-visited URLs from database
        visited_urls = []
        if config.config_id is not None:
            visited_urls = self.pages_repo.get_visited_urls_by_config(config.config_id)
            logger.info("Resume factory: loaded %d visited URLs for config %s (ID: %s)", 
                       len(visited_urls), config.config_path, config.config_id)
            if visited_urls:
                logger.debug("Visited URLs: %s", visited_urls[:5])  # Log first 5 for brevity
        else:
            logger.warning("Resume factory: config_id is None, cannot load visited URLs")
        
        # Create visited tracker and pre-populate with previous URLs
        visited_tracker = VisitedTracker(max_size=self.visited_tracker_max_urls)
        for url in visited_urls:
            visited_tracker.mark(url)
        
        logger.info("Resume factory: pre-populated visited tracker with %d URLs", len(visited_urls))
        
        # Create session with pre-populated tracker
        session = CrawlSession(
            config=config,
            visited_tracker=visited_tracker,
            registry=self.registry,
        )
        
        # Pre-populate session with existing page and link counts from database
        if config.config_id is not None:
            # Get count of already-fetched pages
            fetched_page_ids = self.pages_repo.get_fetched_page_ids_by_config(config.config_id)
            session.pages_crawled = len(fetched_page_ids) if fetched_page_ids else 0
            
            # Get count of existing links if links_repo is available
            if self.links_repo is not None and fetched_page_ids:
                session.links_discovered = self.links_repo.count_links_for_page_ids(fetched_page_ids)
            
            logger.info("Resume factory: pre-populated session counts: pages=%d, links=%d",
                       session.pages_crawled, session.links_discovered)
        
        # Start tracking if registry is available
        session.start_tracking()
        
        return session
