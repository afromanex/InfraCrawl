from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from infracrawl.db.models import CrawlerConfig
from infracrawl.db.engine import make_engine


class ConfigsRepository:
    def __init__(self, engine=None):
        self.engine = engine or make_engine()

    def get_session(self) -> Session:
        return Session(self.engine)

    def upsert_config(self, name: str, root_urls: List[str], max_depth: int, robots: bool = True, refresh_days: Optional[int] = None) -> int:
        with self.get_session() as session:
            q = select(CrawlerConfig).where(CrawlerConfig.name == name)
            c = session.execute(q).scalars().first()
            if c:
                c.root_urls = root_urls
                c.max_depth = max_depth
                c.robots = robots
                c.refresh_days = refresh_days
                session.add(c)
                session.commit()
                return c.config_id
            c = CrawlerConfig(name=name, root_urls=root_urls, max_depth=max_depth, robots=robots, refresh_days=refresh_days)
            session.add(c)
            session.commit()
            session.refresh(c)
            return c.config_id

    def get_config(self, name: str) -> Optional[dict]:
        with self.get_session() as session:
            q = select(CrawlerConfig).where(CrawlerConfig.name == name)
            c = session.execute(q).scalars().first()
            if not c:
                return None
            return {"config_id": c.config_id, "name": c.name, "root_urls": c.root_urls, "max_depth": c.max_depth, "robots": c.robots, "refresh_days": c.refresh_days}

    def get_config_by_id(self, config_id: int) -> Optional[dict]:
        with self.get_session() as session:
            q = select(CrawlerConfig).where(CrawlerConfig.config_id == config_id)
            c = session.execute(q).scalars().first()
            if not c:
                return None
            return {"config_id": c.config_id, "name": c.name, "root_urls": c.root_urls, "max_depth": c.max_depth, "robots": c.robots, "refresh_days": c.refresh_days}

    def list_config_names(self) -> List[str]:
        with self.get_session() as session:
            q = select(CrawlerConfig.name)
            rows = session.execute(q).scalars().all()
            return list(rows)

    def delete_config(self, name: str):
        with self.get_session() as session:
            q = select(CrawlerConfig).where(CrawlerConfig.name == name)
            c = session.execute(q).scalars().first()
            if c:
                session.delete(c)
                session.commit()
