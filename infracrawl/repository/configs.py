from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from infracrawl.db.models import CrawlerConfig as DBCrawlerConfig
from infracrawl.domain import CrawlerConfig
from infracrawl.db.engine import make_engine


class ConfigsRepository:
    def __init__(self, engine=None):
        self.engine = engine or make_engine()

    def get_session(self) -> Session:
        return Session(self.engine)

    def upsert_config(self, config: CrawlerConfig) -> int:
        with self.get_session() as session:
            # Upsert by config_path only. Backwards compatibility by name removed.
            q = select(DBCrawlerConfig).where(DBCrawlerConfig.config_path == config.config_path)
            c = session.execute(q).scalars().first()
            if c:
                c.config_path = config.config_path
                session.add(c)
                session.commit()
                return c.config_id
            c = DBCrawlerConfig(
                config_path=config.config_path
            )
            session.add(c)
            session.commit()
            session.refresh(c)
            return c.config_id

    def get_config(self, config_path: str) -> Optional[CrawlerConfig]:
        """Get config by its file path (e.g., 'starkparks.yml')."""
        with self.get_session() as session:
            q = select(DBCrawlerConfig).where(DBCrawlerConfig.config_path == config_path)
            c = session.execute(q).scalars().first()
            if not c:
                return None
            return CrawlerConfig(
                config_id=c.config_id,
                config_path=c.config_path,
                created_at=c.created_at,
                updated_at=c.updated_at
            )

    def get_config_by_id(self, config_id: int) -> Optional[CrawlerConfig]:
        with self.get_session() as session:
            q = select(DBCrawlerConfig).where(DBCrawlerConfig.config_id == config_id)
            c = session.execute(q).scalars().first()
            if not c:
                return None
            return CrawlerConfig(
                config_id=c.config_id,
                config_path=c.config_path,
                created_at=c.created_at,
                updated_at=c.updated_at
            )

    def list_configs(self) -> List[CrawlerConfig]:
        with self.get_session() as session:
            q = select(DBCrawlerConfig)
            rows = session.execute(q).scalars().all()
            return [CrawlerConfig(
                config_id=c.config_id,
                config_path=c.config_path,
                created_at=c.created_at,
                updated_at=c.updated_at
            ) for c in rows]

    def delete_config(self, name: str):
        with self.get_session() as session:
            # Delete by config_path only. No legacy name-based lookup.
            q = select(DBCrawlerConfig).where(DBCrawlerConfig.config_path == name)
            c = session.execute(q).scalars().first()
            if c:
                session.delete(c)
                session.commit()
