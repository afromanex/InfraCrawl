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
            q = select(DBPage).where(DBPage.page_url == page_url)
            row = session.execute(q).scalars().first()
            if row:
                return row.page_id
            p = DBPage(page_url=page_url)
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
                plain_text=p.plain_text,
                filtered_plain_text=p.filtered_plain_text,
                http_status=p.http_status,
                fetched_at=p.fetched_at,
                config_id=p.config_id
            )

    def upsert_page(self, page_url: str, page_content: Optional[str], http_status: Optional[int], fetched_at: Optional[str], config_id: Optional[int] = None, plain_text: Optional[str] = None, filtered_plain_text: Optional[str] = None) -> Page:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page_url)
            p = session.execute(q).scalars().first()
            if p:
                p.page_content = page_content
                p.plain_text = plain_text
                p.filtered_plain_text = filtered_plain_text
                p.http_status = http_status
                p.fetched_at = fetched_at
                if config_id is not None:
                    p.config_id = config_id
                session.add(p)
                session.commit()
                return Page(
                    page_id=p.page_id,
                    page_url=p.page_url,
                    page_content=p.page_content,
                    plain_text=p.plain_text,
                    filtered_plain_text=p.filtered_plain_text,
                    http_status=p.http_status,
                    fetched_at=p.fetched_at,
                    config_id=p.config_id,
                )
            p = DBPage(page_url=page_url, page_content=page_content, plain_text=plain_text, filtered_plain_text=filtered_plain_text, http_status=http_status, fetched_at=fetched_at, config_id=config_id)
            session.add(p)
            session.commit()
            session.refresh(p)
            return Page(
                page_id=p.page_id,
                page_url=p.page_url,
                page_content=p.page_content,
                plain_text=p.plain_text,
                filtered_plain_text=p.filtered_plain_text,
                http_status=p.http_status,
                fetched_at=p.fetched_at,
                config_id=p.config_id,
            )

    def fetch_pages(self, full: bool = False, limit: Optional[int] = None, offset: Optional[int] = None, config_id: Optional[int] = None) -> List[Page]:
        with self.get_session() as session:
            q = select(DBPage)
            if config_id is not None:
                q = q.where(DBPage.config_id == config_id)
            q = q.order_by(DBPage.page_id)
            if offset:
                q = q.offset(offset)
            if limit:
                q = q.limit(limit)
            rows = session.execute(q).scalars().all()
            return [Page(
                page_id=p.page_id,
                page_url=p.page_url,
                page_content=p.page_content if full else None,
                plain_text=p.plain_text if full else None,
                filtered_plain_text=p.filtered_plain_text if full else None,
                http_status=p.http_status,
                fetched_at=p.fetched_at,
                config_id=p.config_id
            ) for p in rows]

    def get_page_by_id(self, page_id: int) -> Optional[Page]:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_id == page_id)
            p = session.execute(q).scalars().first()
            if not p:
                return None
            return Page(
                page_id=p.page_id,
                page_url=p.page_url,
                page_content=p.page_content,
                plain_text=p.plain_text,
                filtered_plain_text=p.filtered_plain_text,
                http_status=p.http_status,
                fetched_at=p.fetched_at,
                config_id=p.config_id
            )

    def get_page_ids_by_config(self, config_id: int) -> List[int]:
        with self.get_session() as session:
            q = select(DBPage.page_id).where(DBPage.config_id == config_id)
            rows = session.execute(q).scalars().all()
            return rows

    def delete_pages_by_ids(self, ids: List[int]) -> int:
        if not ids:
            return 0
        with self.get_session() as session:
            q = session.query(DBPage).filter(DBPage.page_id.in_(ids))
            deleted = q.delete(synchronize_session=False)
            session.commit()
            return deleted
