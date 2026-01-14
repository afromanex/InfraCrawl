"""Crawl result data model."""
from typing import NamedTuple


class CrawlResult(NamedTuple):
    """Result of a crawl operation.
    
    Provides feedback about what happened during the crawl,
    enabling callers to log metrics and distinguish success from cancellation.
    """
    pages_crawled: int
    """Number of pages successfully fetched and stored"""
    
    stopped: bool
    """True if crawl was stopped early via stop_event, False if completed normally"""
