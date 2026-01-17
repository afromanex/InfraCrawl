from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.domain.config import CrawlerConfig
from infracrawl.domain.crawl_result import CrawlResult

class Crawler:
    """Facade for crawling.

    All default construction/wiring lives in the DI container. This class
    only delegates to an injected `CrawlExecutor`.
    """

    def __init__(self, executor: CrawlExecutor):
        self._executor = executor

    def crawl(self, config: CrawlerConfig, stop_event=None) -> CrawlResult:
        return self._executor.crawl(config, stop_event)
