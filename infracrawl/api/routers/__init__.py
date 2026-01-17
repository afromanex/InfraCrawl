"""API router factory functions."""
from .configs import create_configs_router
from .crawlers import create_crawlers_router
from .systems import create_systems_router
from .auth import create_auth_router

__all__ = [
    "create_configs_router",
    "create_crawlers_router",
    "create_systems_router",
    "create_auth_router",
]
