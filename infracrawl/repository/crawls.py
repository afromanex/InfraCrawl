from typing import Optional
from datetime import datetime
from sqlalchemy import select
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
                raise ValueError(f"CrawlRun with run_id={run_id} not found")
            r.end_timestamp = now
            r.exception = exception
            session.add(r)
            session.commit()

    def get_run(self, run_id: int) -> Optional[DomainCrawlRun]:
        with self.get_session() as session:
            q = select(DBCrawlRun).where(DBCrawlRun.run_id == run_id)
            r = session.execute(q).scalars().first()
            if not r:
                return None
        # Resolve config path if available
        cfg_repo = ConfigsRepository(self.engine)
        cfg_path = None
        if r.config_id is not None:
            cfg = cfg_repo.get_config_by_id(r.config_id)
            if cfg:
                cfg_path = cfg.config_path
        return DomainCrawlRun(r.run_id, r.config_id, cfg_path, r.start_timestamp, r.end_timestamp, r.exception)

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

    def clear_incomplete_runs(self, config_id: int, within_seconds: Optional[int] = None, message: Optional[str] = None) -> int:
        """Mark recent incomplete runs for a config as finished and delete their pages/links.

        Returns the number of runs marked finished.
        """
        from datetime import timedelta

        # lazy imports to avoid cycles
        from infracrawl.repository.pages import PagesRepository
        from infracrawl.repository.links import LinksRepository

        now = datetime.utcnow()
        cutoff = None
        if within_seconds is not None:
            cutoff = now - timedelta(seconds=within_seconds)

        with self.get_session() as session:
            q = select(DBCrawlRun).where(DBCrawlRun.config_id == config_id, DBCrawlRun.end_timestamp.is_(None))
            if cutoff is not None:
                q = q.where(DBCrawlRun.start_timestamp >= cutoff)
            rows = session.execute(q).scalars().all()
            count = 0
            for r in rows:
                r.end_timestamp = now
                r.exception = message or "job found incomplete on startup"
                session.add(r)
                count += 1
            if count:
                session.commit()
            else:
                session.rollback()

        if count:
            # best-effort cleanup of pages/links for this config
            pages_repo = PagesRepository(self.engine)
            links_repo = LinksRepository(self.engine)
            try:
                page_ids = pages_repo.get_page_ids_by_config(config_id)
                if page_ids:
                    links_repo.delete_links_for_page_ids(page_ids)
                    pages_repo.delete_pages_by_ids(page_ids)
            except Exception:
                import logging

                logging.exception("Failed cleaning pages/links for config %s", config_id)

        return count
