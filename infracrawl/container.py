"""Dependency injection container for the application."""
from dependency_injector import containers, providers

from infracrawl.db.engine import make_engine
from infracrawl.repository.pages import PagesRepository
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawler import Crawler
from infracrawl.services.crawl_policy import CrawlPolicy
from infracrawl.services.http_service import HttpService
from infracrawl.services.robots_service import RobotsService
from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.services.link_processor import LinkProcessor
from infracrawl.services.content_review_service import ContentReviewService


class Container(containers.DeclarativeContainer):
    """Dependency injection container for InfraCrawl application."""
    
    # Configuration
    config = providers.Configuration()
    
    # Database engine - Singleton to reuse connection pool
    db_engine = providers.Singleton(
        make_engine,
        database_url=config.database_url
    )
    
    # Repositories - Singleton instances
    pages_repository = providers.Singleton(
        PagesRepository
    )
    
    links_repository = providers.Singleton(
        LinksRepository
    )
    
    configs_repository = providers.Singleton(
        ConfigsRepository
    )
    
    # Services - Singleton instances
    http_service = providers.Singleton(
        HttpService,
        user_agent=config.user_agent.as_(str),
        timeout=config.http_timeout.as_(int)
    )
    
    robots_service = providers.Singleton(
        RobotsService,
        http_service=http_service,
        user_agent=config.user_agent.as_(str)
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
        delay=config.crawl_delay.as_(float),
        user_agent=config.user_agent.as_(str),
        http_service=http_service,
        content_review_service=content_review_service,
        robots_service=robots_service,
        link_processor=link_processor,
        fetch_persist_service=page_fetch_persist_service,
        crawl_policy=crawl_policy
    )
