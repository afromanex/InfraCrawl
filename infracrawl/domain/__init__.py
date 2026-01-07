"""Domain objects for InfraCrawl - explicit re-exports to satisfy linters."""
from .page import Page as Page
from .link import Link as Link
from .config import CrawlerConfig as CrawlerConfig

__all__ = ["Page", "Link", "CrawlerConfig"]
