from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from infracrawl.db.models import Page as DBPage
from infracrawl.domain import Page
from infracrawl.db.engine import make_engine


class PagesRepository:
    """Repository for Page database operations."""
    def __init__(self, engine=None):
        # TODO: Creating new engine per repo instance is expensive
        # CLAUDE: Use dependency injection - pass shared engine from main(). Implement later when scaling.
        self.engine = engine or make_engine()

    def get_session(self) -> Session:
        # TODO: Returns raw Session - no error handling for connection failures
        # CLAUDE: SQLAlchemy Session context manager handles rollback. Connection pool retries. Current approach is fine.
        return Session(self.engine)
    
    def _to_domain(self, db_page: DBPage, full: bool = True) -> Page:
        """Convert database Page to domain Page."""
        return Page(
            page_id=db_page.page_id,
            page_url=db_page.page_url,
            page_content=db_page.page_content if full else None,
            plain_text=db_page.plain_text if full else None,
            filtered_plain_text=db_page.filtered_plain_text if full else None,
            http_status=db_page.http_status,
            fetched_at=db_page.fetched_at,
            config_id=db_page.config_id
        )

    def ensure_page(self, page_url: str) -> int:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page_url)
            row = session.execute(q).scalars().first()
            if row:
                return row.page_id
            p = DBPage(page_url=page_url)
            session.add(p)
            # TODO: No handling of unique constraint violation if concurrent insert happens
            # CLAUDE: Two crawlers inserting same URL simultaneously. Use INSERT ... ON CONFLICT or catch IntegrityError and retry query.
            session.commit()
            session.refresh(p)
            return p.page_id

    def get_page_by_url(self, page_url: str) -> Optional[Page]:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page_url)
            p = session.execute(q).scalars().first()
            if not p:
                return None
            return self._to_domain(p)

    # TODO: 7 parameters - should accept Page domain object
    # TODO: http_status typed as Optional[int] but accepts string from caller - type mismatch
    # TODO: fetched_at typed as Optional[str] but should be datetime
    # CLAUDE: These todos remain valid but defer refactor - would break all callers. Consider for v2 API.
    def upsert_page(self, page_url: str, page_content: Optional[str], http_status: Optional[int], fetched_at: Optional[str], config_id: Optional[int] = None, plain_text: Optional[str] = None, filtered_plain_text: Optional[str] = None) -> Page:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page_url)
            p = session.execute(q).scalars().first()
            if p:
                # TODO: No optimistic locking - concurrent updates will overwrite
                # CLAUDE: Add version column if this becomes issue. Unlikely with current single-crawler design.
                p.page_content = page_content
                p.plain_text = plain_text
                p.filtered_plain_text = filtered_plain_text
                p.http_status = http_status
                p.fetched_at = fetched_at
                if config_id is not None:
                    p.config_id = config_id
                session.add(p)
                session.commit()
                return self._to_domain(p)
            p = DBPage(page_url=page_url, page_content=page_content, plain_text=plain_text, filtered_plain_text=filtered_plain_text, http_status=http_status, fetched_at=fetched_at, config_id=config_id)
            session.add(p)
            session.commit()
            session.refresh(p)
            return self._to_domain(p)

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
            return [self._to_domain(row, full=full) for row in rows]

    def get_page_by_id(self, page_id: int) -> Optional[Page]:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_id == page_id)
            p = session.execute(q).scalars().first()
            if not p:
                return None
            return self._to_domain(p)

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
