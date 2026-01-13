from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from infracrawl import config


def make_engine(database_url: Optional[str] = None) -> Engine:
    database_url = database_url or config.DATABASE_URL
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    engine = create_engine(database_url)
    return engine
