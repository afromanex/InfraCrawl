import logging
from typing import Optional

from infracrawl.domain.crawl_result import CrawlResult
from infracrawl.services.configured_crawl_provider import ConfiguredCrawlProviderFactory

logger = logging.getLogger(__name__)

class CrawlExecutor:
    """Thin orchestration layer for multi-root crawls.

    Builds a provider per config, iterates root URLs, and coordinates
    high-level concerns (logging, registry updates, result aggregation).
    The provider owns all crawl traversal logic.
    """

    def __init__(
        self,
        *,
        provider_factory: ConfiguredCrawlProviderFactory,
        crawl_registry=None,
    ):
        self.provider_factory = provider_factory
        self.crawl_registry = crawl_registry

    def _is_stopped(self, stop_event) -> bool:
        return stop_event is not None and getattr(stop_event, "is_set", lambda: False)()

    def _update_registry_progress(self, crawl_id: str, pages_fetched: int, links_found: int = 0) -> None:
        """Update the crawl registry with current progress."""
        if self.crawl_registry is not None and crawl_id is not None:
            try:
                self.crawl_registry.update(
                    crawl_id,
                    pages_fetched=pages_fetched,
                    links_found=links_found,
                )
            except Exception as e:
                logger.warning("Failed to update registry progress: %s", e)

    def crawl(self, config, stop_event=None, crawl_id: Optional[str] = None) -> CrawlResult:
        if config is None:
            raise ValueError("config is required for crawl")

        # Build per-crawl provider (includes context/tracking and traversal logic).
        provider = self.provider_factory.build(config)
        context = provider.context
        logger.info("Crawl started for config %s", getattr(config, "config_id", None))

        stopped = False
        roots = getattr(context.config, "root_urls", []) or []
        for root_url in roots:
            if self._is_stopped(stop_event):
                logger.info("Crawl cancelled before starting root %s", root_url)
                stopped = True
                break
            context.set_root(root_url)
            context.set_current_depth(context.max_depth)
            result = provider.crawl_from(root_url, stop_event)
            if result[1]:
                stopped = True
                break

        # Update registry with final page count
        if crawl_id is not None:
            self._update_registry_progress(crawl_id, context.pages_crawled)

        logger.info(
            "Crawl completed for config %s: pages=%s stopped=%s",
            getattr(config, "config_id", None),
            context.pages_crawled,
            stopped,
        )

        return CrawlResult(pages_crawled=context.pages_crawled, stopped=stopped)
