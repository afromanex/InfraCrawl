"""Dependency injection container for the application."""
from dependency_injector import containers, providers
import requests

from infracrawl.db.engine import make_engine
from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawler import Crawler
from infracrawl.services.crawl_policy import CrawlPolicy
from infracrawl.services.http_service import HttpService
from infracrawl.services.fetcher import HttpServiceFetcher
from infracrawl.services.fetcher_factory import FetcherFactory
from infracrawl.services.headless_browser_fetcher import PlaywrightHeadlessFetcher, PlaywrightHeadlessOptions
from infracrawl.services.robots_service import RobotsService
from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.services.link_processor import LinkProcessor
from infracrawl.services.content_review_service import ContentReviewService
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry
from infracrawl.services.scheduler_service import SchedulerService
from infracrawl.repository.crawls import CrawlsRepository
from infracrawl import config as env
from sqlalchemy.orm import sessionmaker


ENV = {
    "DATABASE_URL": env.get_optional_str_env("DATABASE_URL"),
    "USER_AGENT": env.get_str_env("USER_AGENT", "InfraCrawl/0.1"),
    "HTTP_TIMEOUT": env.get_int_env("HTTP_TIMEOUT", 10),
    "CRAWL_DELAY": env.get_float_env("CRAWL_DELAY", 1.0),
    "INFRACRAWL_CONFIG_WATCH_INTERVAL": env.get_int_env("INFRACRAWL_CONFIG_WATCH_INTERVAL", 60),
    "INFRACRAWL_RECOVERY_MODE": env.get_str_env("INFRACRAWL_RECOVERY_MODE", "restart").strip().lower(),
    "INFRACRAWL_RECOVERY_WITHIN_SECONDS": env.get_optional_int_env("INFRACRAWL_RECOVERY_WITHIN_SECONDS"),
    "INFRACRAWL_RECOVERY_MESSAGE": env.get_str_env("INFRACRAWL_RECOVERY_MESSAGE", "job found incomplete on startup"),
}


class Container(containers.DeclarativeContainer):
    """Dependency injection container for InfraCrawl application."""
    
    # Configuration
    config = providers.Configuration(default=ENV)
    
    # Database engine - Singleton to reuse connection pool
    db_engine = providers.Singleton(
        make_engine,
        database_url=config.DATABASE_URL
    )
    # Session factory bound to the engine
    session_factory = providers.Factory(
        sessionmaker,
        bind=db_engine,
        future=True
    )
    
    # Repositories - Singleton instances
    pages_repository = providers.Singleton(
        PagesRepository,
        session_factory=session_factory
    )
    
    links_repository = providers.Singleton(
        LinksRepository,
        session_factory=session_factory
    )
    
    configs_repository = providers.Singleton(
        ConfigsRepository,
        session_factory=session_factory
    )

    crawls_repository = providers.Singleton(
        CrawlsRepository,
        session_factory=session_factory
    )

    crawl_registry = providers.Singleton(
        InMemoryCrawlRegistry
    )
    
    # Services - Singleton instances
    http_service = providers.Singleton(
        HttpService,
        user_agent=config.USER_AGENT.as_(str),
        http_client=providers.Object(requests.get),
        timeout=config.HTTP_TIMEOUT.as_(int)
    )

    page_fetcher = providers.Singleton(
        HttpServiceFetcher,
        http_service=http_service,
    )

    headless_fetcher = providers.Singleton(
        PlaywrightHeadlessFetcher,
        user_agent=config.USER_AGENT.as_(str),
        options=providers.Factory(
            PlaywrightHeadlessOptions,
            timeout_ms=providers.Callable(lambda t: t * 1000, config.HTTP_TIMEOUT.as_(int)),
        ),
    )

    fetcher_factory = providers.Singleton(
        FetcherFactory,
        http_fetcher=page_fetcher,
        headless_fetcher=headless_fetcher,
    )
    
    robots_service = providers.Singleton(
        RobotsService,
        http_service=http_service,
        user_agent=config.USER_AGENT.as_(str)
    )
    
    content_review_service = providers.Singleton(
        ContentReviewService
    )
    
    crawl_policy = providers.Singleton(
        CrawlPolicy,
        pages_repo=pages_repository,
        robots_service=robots_service
    )
    
    page_fetch_persist_service = providers.Singleton(
        PageFetchPersistService,
        http_service=http_service,
        pages_repo=pages_repository
    )
    
    link_processor = providers.Singleton(
        LinkProcessor,
        content_review_service=content_review_service,
        pages_repo=pages_repository,
        links_repo=links_repository
    )
    
    config_service = providers.Singleton(
        ConfigService,
        configs_repo=configs_repository
    )
    
    # Crawler - Factory to allow multiple instances with different configs
    crawler = providers.Factory(
        Crawler,
        pages_repo=pages_repository,
        links_repo=links_repository,
        delay=config.CRAWL_DELAY.as_(float),
        user_agent=config.USER_AGENT.as_(str),
        http_service=http_service,
        fetcher=page_fetcher,
        headless_fetcher=headless_fetcher,
        fetcher_factory=fetcher_factory,
        content_review_service=content_review_service,
        robots_service=robots_service,
        link_processor=link_processor,
        fetch_persist_service=page_fetch_persist_service,
        crawl_policy=crawl_policy
    )

    # Scheduler - Singleton instance
    scheduler_service = providers.Singleton(
        SchedulerService,
        config_provider=config_service,
        start_crawl_callback=crawler.provided.crawl,
        crawl_registry=crawl_registry,
        crawls_repo=crawls_repository,
        config_watch_interval_seconds=config.INFRACRAWL_CONFIG_WATCH_INTERVAL.as_(int),
        recovery_mode=config.INFRACRAWL_RECOVERY_MODE.as_(str),
        recovery_within_seconds=config.INFRACRAWL_RECOVERY_WITHIN_SECONDS,
        recovery_message=config.INFRACRAWL_RECOVERY_MESSAGE.as_(str),
    )
