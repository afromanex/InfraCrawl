from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from infracrawl import config

# Simple cache to avoid creating multiple Engine objects in the same process.
_ENGINE: Optional[Engine] = None


def make_engine(database_url: Optional[str] = None) -> Engine:
    """Create or return a cached SQLAlchemy Engine for `database_url`.

    Caches a single Engine instance per process to avoid the cost of
    creating many engines when repository instances are created.
    """
    global _ENGINE
    database_url = database_url or config.DATABASE_URL
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    if _ENGINE is None:
        _ENGINE = create_engine(database_url)
    return _ENGINE
