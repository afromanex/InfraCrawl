from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from infracrawl.db.models import Page
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

    def get_page_by_url(self, page_url: str) -> Optional[dict]:
        with self.get_session() as session:
            q = select(Page).where(Page.page_url == page_url)
            p = session.execute(q).scalars().first()
            if not p:
                return None
            return {"page_id": p.page_id, "page_url": p.page_url, "fetched_at": p.fetched_at}

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

    def fetch_pages(self, full: bool = False, limit: Optional[int] = None) -> List[dict]:
        with self.get_session() as session:
            q = select(Page).order_by(Page.page_id)
            if limit:
                q = q.limit(limit)
            rows = session.execute(q).scalars().all()
            out = []
            for p in rows:
                d = {"page_id": p.page_id, "page_url": p.page_url, "http_status": p.http_status, "fetched_at": (p.fetched_at.isoformat() if p.fetched_at else None)}
                if full:
                    d["page_content"] = p.page_content
                out.append(d)
            return out
