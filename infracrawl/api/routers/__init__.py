"""API router factory functions."""
from .configs import create_configs_router
from .pages import create_pages_router
from .crawlers import create_crawlers_router
from .systems import create_systems_router

__all__ = [
    "create_configs_router",
    "create_pages_router",
    "create_crawlers_router",
    "create_systems_router",
]
