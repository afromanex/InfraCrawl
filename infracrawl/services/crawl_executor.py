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
        """Execute a crawl for the given session.
        
        Args:
            session: Pre-configured CrawlSession with config, tracking, and registry details
            
        Returns:
            CrawlResult with pages crawled and stopped status
        """
        if session is None or session.config is None:
            raise ValueError("session with config is required for crawl")

        # Build per-crawl provider from session
        provider = self.provider_factory.build(session)
        logger.info("Crawl started for config %s", session.config.config_id)

        was_cancelled = False
        roots = session.config.root_urls or []
        for root_url in roots:
            # Create page object for root URL
            page = Page(page_url=root_url)
            
            # If this is a resumed crawl (visited tracker already populated),
            # use crawl_children_from to skip re-fetching but still process children
            if session.visited_tracker.is_visited(root_url):
                was_cancelled = provider.crawl_children_from(page, session.config.max_depth)
            else:
                was_cancelled = provider.crawl_from(page, session.config.max_depth)
            
            if was_cancelled:
                break

        # Update registry with final page count via session
        # Note: session.pages_crawled is already maintained by the provider
        session.update_progress()

        logger.info(
            "Crawl completed for config %s: pages=%s stopped=%s",
            session.config.config_id,
            provider.context,
            was_cancelled,
        )

        return CrawlResult(pages_crawled=provider.context.pages_crawled, stopped=was_cancelled)
