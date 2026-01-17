from infracrawl.domain.crawl_session import CrawlSession
from infracrawl.services.configured_crawl_provider import ConfiguredCrawlProvider
from infracrawl.services.fetcher_factory import FetcherFactory


class ConfiguredCrawlProviderFactory:
    """Factory that builds fully-equipped crawl providers.

    Receives all necessary collaborators and wires them into providers per session.
    The session is expected to be created externally (typically by CrawlSessionFactory).
    """

    def __init__(
        self,
        fetcher_factory: FetcherFactory,
        pages_repo,
        crawl_policy,
        link_processor,
        fetch_persist_service,
        delay_seconds: float,
    ):
        self.fetcher_factory = fetcher_factory
        self.pages_repo = pages_repo
        self.crawl_policy = crawl_policy
        self.link_processor = link_processor
        self.fetch_persist_service = fetch_persist_service
        self.delay_seconds = delay_seconds

    def build(self, session: CrawlSession) -> ConfiguredCrawlProvider:
        """Build a provider for the given session.
        
        Args:
            session: Pre-configured CrawlSession with config, tracking, etc.
            
        Returns:
            Configured provider ready to execute the crawl
        """
        config = session.config
        fetcher = self.fetcher_factory.get(config.fetch_mode, config=config)
        return ConfiguredCrawlProvider(
            fetcher=fetcher,
            context=session,
            pages_repo=self.pages_repo,
            crawl_policy=self.crawl_policy,
            link_processor=self.link_processor,
            fetch_persist_service=self.fetch_persist_service,
            delay_seconds=self.delay_seconds,
        )
