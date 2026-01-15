from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.crawl_result import CrawlResult

class Crawler:
    """Facade for crawling.

    All default construction/wiring lives in the DI container. This class
    only delegates to an injected `CrawlExecutor`.
    """

    def __init__(self, executor: CrawlExecutor):
        self._executor = executor

    def _is_stopped(self, stop_event) -> bool:
        return self._executor._is_stopped(stop_event)

    def _fetch_and_store(self, url: str, context, stop_event=None):
        return self._executor.fetch_and_store(url, context, stop_event)

    def _process_links(
        self,
        url: str,
        body: str,
        from_id: int,
        context,
        depth: int,
        _crawl_from=None,
        stop_event=None,
    ) -> tuple[int, bool]:
        return self._executor.process_links(url, body, from_id, context, depth, _crawl_from, stop_event)

    def crawl(self, config: CrawlerConfig, stop_event=None) -> CrawlResult:
        return self._executor.crawl(config, stop_event)

    def _crawl_from(self, url: str, depth: int, context: CrawlContext, stop_event=None) -> tuple[int, bool]:
        return self._executor.crawl_from(url, depth, context, stop_event)

        
