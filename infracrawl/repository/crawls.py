from typing import Optional
from datetime import datetime
from sqlalchemy import insert, update, select
from sqlalchemy.orm import Session

from infracrawl.db.engine import make_engine
from infracrawl.db.models import CrawlRun as DBCrawlRun
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain import CrawlRun as DomainCrawlRun


class CrawlsRepository:
    def __init__(self, engine=None):
        self.engine = engine or make_engine()

    def get_session(self) -> Session:
        return Session(self.engine)

    def create_run(self, config_id: Optional[int]) -> int:
        now = datetime.utcnow()
        with self.get_session() as session:
            r = DBCrawlRun(config_id=config_id, start_timestamp=now)
            session.add(r)
            session.commit()
            session.refresh(r)
            return r.run_id

    def finish_run(self, run_id: int, exception: Optional[str] = None):
        now = datetime.utcnow()
        with self.get_session() as session:
            q = select(DBCrawlRun).where(DBCrawlRun.run_id == run_id)
            r = session.execute(q).scalars().first()
            if not r:
                return False
            r.end_timestamp = now
            r.exception = exception
            session.add(r)
            session.commit()
            return True

    def get_run(self, run_id: int) -> Optional[DBCrawlRun]:
        with self.get_session() as session:
            q = select(DBCrawlRun).where(DBCrawlRun.run_id == run_id)
            return session.execute(q).scalars().first()

    def list_runs(self, limit: int = 20):
        """Return recent runs as domain objects, including config path if available."""
        with self.get_session() as session:
            q = select(DBCrawlRun).order_by(DBCrawlRun.run_id.desc()).limit(limit)
            rows = session.execute(q).scalars().all()
        # Resolve config paths using ConfigsRepository (may return None)
        cfg_repo = ConfigsRepository(self.engine)
        out = []
        for r in rows:
            cfg_path = None
            if r.config_id is not None:
                cfg = cfg_repo.get_config_by_id(r.config_id)
                if cfg:
                    cfg_path = cfg.config_path
            out.append(DomainCrawlRun(r.run_id, r.config_id, cfg_path, r.start_timestamp, r.end_timestamp, r.exception))
        return out
