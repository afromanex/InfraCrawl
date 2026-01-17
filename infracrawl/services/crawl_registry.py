"""Backward-compatible shim: re-export new crawl_registry package objects."""

from infracrawl.services.crawl_registry.models import CrawlHandle, CrawlRecord  # noqa: F401
from infracrawl.services.crawl_registry.registry import InMemoryCrawlRegistry  # noqa: F401

__all__ = ["CrawlRecord", "CrawlHandle", "InMemoryCrawlRegistry"]
