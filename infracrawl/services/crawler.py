from infracrawl.services.crawl_executor import CrawlExecutor
from infracrawl.domain import CrawlSession
from infracrawl.domain.crawl_result import CrawlResult

class Crawler:
    """Facade for crawling.

    All default construction/wiring lives in the DI container. This class
    only delegates to an injected `CrawlExecutor`.
    """

    def __init__(self, executor: CrawlExecutor):
        self._executor = executor

    def crawl(self, session: CrawlSession) -> CrawlResult:
        """Execute a crawl for the given session."""
        return self._executor.crawl(session)
