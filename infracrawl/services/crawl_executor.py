import logging

from infracrawl.domain import CrawlSession
from infracrawl.domain.page import Page
from infracrawl.domain.crawl_result import CrawlResult
from infracrawl.services.configured_crawl_provider_factory import ConfiguredCrawlProviderFactory

logger = logging.getLogger(__name__)

class CrawlExecutor:
    """Thin orchestration layer for multi-root crawls.

    Accepts a pre-configured CrawlSession, builds a provider, and coordinates
    high-level concerns (logging, result aggregation).
    The session carries all configuration and tracking state, including registry updates.
    The provider owns all crawl traversal logic.
    """

    def __init__(
        self,
        *,
        provider_factory: ConfiguredCrawlProviderFactory,
    ):
        self.provider_factory = provider_factory

    def crawl(self, session: CrawlSession) -> CrawlResult:
        """Execute an iterative depth-based crawl for the given session.
        
        Crawling proceeds by depth level:
        - Depth 0: Root URLs (fetched, links stored as undiscovered)
        - Depth 1: All pages discovered from roots (fetched, their links stored)
        - Depth N: All pages discovered at depth N-1 (up to max_depth)
        
        This allows resumption: if interrupted, undiscovered pages remain in DB.
        
        Args:
            session: Pre-configured CrawlSession with config, tracking, and registry details
            
        Returns:
            CrawlResult with pages crawled and stopped status
        """
        if session is None or session.config is None:
            raise ValueError("session with config is required for crawl")

        # Build per-crawl provider from session
        provider = self.provider_factory.build(session)
        logger.info("Crawl started for config %s (iterative depth-based crawling)", session.config.config_id)

        was_cancelled = False
        max_depth = session.config.max_depth
        
        # Start depth: 0 for roots, or resume from interrupted depth
        current_depth = 0
        if len(session.visited_tracker._visited) > 0:
            logger.info("Resuming crawl with %d pre-loaded visited URLs", len(session.visited_tracker._visited))
            current_depth = 0  # Always start at roots for resume, they'll be skipped if already visited
        
        while current_depth is None or current_depth <= (max_depth or float('inf')):
            if was_cancelled:
                logger.info("Crawl cancelled at depth %s", current_depth)
                break
            
            # Phase 1: Root URLs at depth 0
            if current_depth == 0:
                logger.info("Crawling depth 0: root URLs")
                roots = session.config.root_urls or []
                logger.info("Processing %d root URL(s)", len(roots))
                
                for root_url in roots:
                    if was_cancelled:
                        break
                    
                    page = Page(page_url=root_url, config_id=session.config.config_id)
                    page.discovered_depth = 0  # Mark as root
                    
                    is_visited = session.visited_tracker.is_visited(root_url)
                    logger.info("  Root: %s (already visited: %s)", root_url, is_visited)
                    
                    if is_visited:
                        # Resume: skip refetch but process links to discover children
                        was_cancelled = provider.crawl_children_from(page, max_depth)
                    else:
                        # Fresh: fetch and discover links
                        was_cancelled = provider.crawl_from(page, max_depth)
            else:
                # Phase 2+: Crawl all discovered pages at current depth
                logger.info("Crawling depth %s: discovered pages", current_depth)
                undiscovered = provider.pages_repo.get_undiscovered_urls_by_depth(
                    session.config.config_id, 
                    current_depth,
                    limit=1000
                )
                
                if not undiscovered:
                    logger.info("No more undiscovered pages at depth %s, stopping", current_depth)
                    break
                
                logger.info("Found %d undiscovered pages at depth %s", len(undiscovered), current_depth)
                
                for page_url in undiscovered:
                    if was_cancelled:
                        break
                    
                    page = Page(page_url=page_url, config_id=session.config.config_id)
                    page.discovered_depth = current_depth
                    logger.info("  Crawling: %s (depth %s)", page_url, current_depth)
                    was_cancelled = provider.crawl_from(page, max_depth)
            
            current_depth += 1

        # Update registry with final page count via session
        session.update_progress()

        logger.info(
            "Crawl completed for config %s (depth reached %s): pages=%s stopped=%s",
            session.config.config_id,
            current_depth - 1,
            provider.context.pages_crawled,
            was_cancelled,
        )

        return CrawlResult(pages_crawled=provider.context.pages_crawled, stopped=was_cancelled)
