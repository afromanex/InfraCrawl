from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from infracrawl.db.models import Page as DBPage
from infracrawl.domain import Page
from infracrawl.db.engine import make_engine


class PagesRepository:
    def __init__(self, engine=None):
        self.engine = engine or make_engine()

    def get_session(self) -> Session:
        return Session(self.engine)

    def ensure_page(self, page_url: str) -> int:
        with self.get_session() as session:
            q = select(Page).where(Page.page_url == page_url)
            row = session.execute(q).scalars().first()
            if row:
                return row.page_id
            p = Page(page_url=page_url)
            session.add(p)
            session.commit()
            session.refresh(p)
            return p.page_id

    def get_page_by_url(self, page_url: str) -> Optional[Page]:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page_url)
            p = session.execute(q).scalars().first()
            if not p:
                return None
            return Page(
                page_id=p.page_id,
                page_url=p.page_url,
                page_content=p.page_content,
                http_status=p.http_status,
                fetched_at=p.fetched_at,
                config_id=p.config_id
            )

    def upsert_page(self, page_url: str, page_content: Optional[str], http_status: Optional[int], fetched_at: Optional[str], config_id: Optional[int] = None) -> int:
        with self.get_session() as session:
            q = select(Page).where(Page.page_url == page_url)
            p = session.execute(q).scalars().first()
            if p:
                p.page_content = page_content
                p.http_status = http_status
                p.fetched_at = fetched_at
                if config_id is not None:
                    p.config_id = config_id
                session.add(p)
                session.commit()
                return p.page_id
            p = Page(page_url=page_url, page_content=page_content, http_status=http_status, fetched_at=fetched_at, config_id=config_id)
            session.add(p)
            session.commit()
            session.refresh(p)
            return p.page_id

    def fetch_pages(self, full: bool = False, limit: Optional[int] = None) -> List[Page]:
        with self.get_session() as session:
            q = select(DBPage).order_by(DBPage.page_id)
            if limit:
                q = q.limit(limit)
            rows = session.execute(q).scalars().all()
            return [Page(
                page_id=p.page_id,
                page_url=p.page_url,
                page_content=p.page_content if full else None,
                http_status=p.http_status,
                fetched_at=p.fetched_at,
                config_id=p.config_id
            ) for p in rows]
