from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from infracrawl.db.models import Page as DBPage
from infracrawl.domain import Page
from infracrawl.db.engine import make_engine


class PagesRepository:
    """Repository for Page database operations.

    Requires an explicit `session_factory` (callable returning a `Session`).
    """
    def __init__(self, session_factory):
        self.session_factory = session_factory

    @staticmethod
    def _sanitize_text(val: Optional[str]) -> Optional[str]:
        """Remove NUL (\x00) characters from text fields to satisfy DB constraints.

        Postgres TEXT columns cannot contain NULs; some fetched content (e.g., PDFs
        or binary responses misclassified as text) may include NUL bytes. Strip them
        before persisting.
        """
        if isinstance(val, str):
            return val.replace("\x00", "")
        return val

    def get_session(self) -> Session:
        return self.session_factory()
    
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
            config_id=db_page.config_id,
            content_hash=db_page.content_hash,
            discovered_depth=db_page.discovered_depth,
        )

    def ensure_page(self, page) -> None:
        """Ensure page exists in database and set page.page_id.
        
        Args:
            page: Page object with page_url. Will have page_id set.
        """
        page_url = page.page_url
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page_url)
            row = session.execute(q).scalars().first()
            if row:
                page.page_id = row.page_id
                return
            p = DBPage(
                page_url=page_url,
                config_id=page.config_id if hasattr(page, 'config_id') else None,
                discovered_depth=page.discovered_depth if hasattr(page, 'discovered_depth') else None
            )
            session.add(p)
            # Handle possible unique constraint races: if another worker inserted
            # the same URL concurrently, catch IntegrityError, rollback and re-query.
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                q = select(DBPage).where(DBPage.page_url == page_url)
                existing = session.execute(q).scalars().first()
                if existing:
                    page.page_id = existing.page_id
                    return
                raise
            session.refresh(p)
            page.page_id = p.page_id
    
    def ensure_pages_batch(self, page_urls: List[str], discovered_depth: Optional[int] = None, config_id: Optional[int] = None) -> dict[str, int]:
        """Ensure multiple pages exist and return mapping of URL -> page_id.
        
        Batch operation to reduce N+1 queries. Returns dict mapping each URL to its page_id.
        Sets discovered_depth and config_id on newly created pages if provided.
        """
        if not page_urls:
            return {}
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info("ensure_pages_batch: urls=%d, discovered_depth=%s, config_id=%s", len(page_urls), discovered_depth, config_id)
        
        with self.get_session() as session:
            # Find existing pages
            q = select(DBPage).where(DBPage.page_url.in_(page_urls))
            existing = session.execute(q).scalars().all()
            url_to_id = {p.page_url: p.page_id for p in existing}
            
            # Insert missing pages
            missing_urls = set(page_urls) - set(url_to_id.keys())
            if missing_urls:
                logger.info("Creating %d new pages with discovered_depth=%s, config_id=%s", len(missing_urls), discovered_depth, config_id)
                new_pages = [DBPage(page_url=url, discovered_depth=discovered_depth, config_id=config_id) for url in missing_urls]
                session.add_all(new_pages)
                session.commit()
                for p in new_pages:
                    session.refresh(p)
                    url_to_id[p.page_url] = p.page_id
            
            return url_to_id

    def get_page_by_url(self, page_url: str) -> Optional[Page]:
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page_url)
            p = session.execute(q).scalars().first()
            if not p:
                return None
            return self._to_domain(p)

    def upsert_page(self, page: Page) -> Page:
        """Upsert page using domain object. Accepts Page with page_id (ignored for upsert).
        
        Deduplication: If config_id and content_hash are both present and non-empty,
        check for an existing page with the same (config_id, content_hash) pair.
        If found, return the existing page without creating a duplicate.
        """
        # Check for dedup: if config_id and content_hash both exist, look for existing
        if (page.config_id is not None and 
            getattr(page, 'content_hash', None) is not None):
            with self.get_session() as session:
                q = select(DBPage).where(
                    (DBPage.config_id == page.config_id) &
                    (DBPage.content_hash == page.content_hash)
                )
                existing = session.execute(q).scalars().first()
                if existing:
                    # Return the existing page without modifying or creating a new one
                    return self._to_domain(existing)
        
        with self.get_session() as session:
            q = select(DBPage).where(DBPage.page_url == page.page_url)
            p = session.execute(q).scalars().first()
            if p:
                # TODO: No optimistic locking - concurrent updates will overwrite
                # CLAUDE: Add version column if this becomes issue. Unlikely with current single-crawler design.
                p.page_content = self._sanitize_text(page.page_content)
                p.plain_text = self._sanitize_text(page.plain_text)
                p.filtered_plain_text = self._sanitize_text(page.filtered_plain_text)
                p.http_status = page.http_status
                # Coerce ISO datetime strings (e.g. ending with 'Z') to datetime
                if isinstance(page.fetched_at, datetime):
                    p.fetched_at = page.fetched_at
                elif isinstance(page.fetched_at, str):
                    try:
                        p.fetched_at = datetime.fromisoformat(page.fetched_at.replace('Z', '+00:00'))
                    except ValueError:
                        p.fetched_at = None
                else:
                    p.fetched_at = None
                if page.config_id is not None:
                    p.config_id = page.config_id
                # Update content_hash if provided
                if getattr(page, 'content_hash', None) is not None:
                    p.content_hash = page.content_hash
                session.add(p)
                session.commit()
                session.refresh(p)
                return self._to_domain(p)
            
            if isinstance(page.fetched_at, datetime):
                fetched_at_val = page.fetched_at
            elif isinstance(page.fetched_at, str):
                try:
                    fetched_at_val = datetime.fromisoformat(page.fetched_at.replace('Z', '+00:00'))
                except ValueError:
                    fetched_at_val = None
            else:
                fetched_at_val = None
            p = DBPage(
                page_url=page.page_url,
                page_content=self._sanitize_text(page.page_content),
                plain_text=self._sanitize_text(page.plain_text),
                filtered_plain_text=self._sanitize_text(page.filtered_plain_text),
                http_status=page.http_status,
                fetched_at=fetched_at_val,
                config_id=page.config_id,
                content_hash=getattr(page, 'content_hash', None),
            )
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

    def get_fetched_page_ids_by_config(self, config_id: int) -> List[int]:
        """Get page IDs for a config that have been fetched (have content).
        
        Args:
            config_id: The crawler config ID
            
        Returns:
            List of page IDs that have page_content (not NULL)
        """
        with self.get_session() as session:
            q = select(DBPage.page_id).where(
                (DBPage.config_id == config_id) &
                (DBPage.page_content.is_not(None))
            )
            rows = session.execute(q).scalars().all()
            return rows

    def get_visited_urls_by_config(self, config_id: int) -> List[str]:
        """Get all page URLs that have been visited for a given config.
        
        Only returns pages that have content (were actually fetched), not pages
        that were only discovered but never crawled.
        
        Args:
            config_id: The crawler config ID
            
        Returns:
            List of page URLs that have been crawled (have content)
        """
        with self.get_session() as session:
            q = select(DBPage.page_url).where(
                DBPage.config_id == config_id,
                DBPage.page_content.isnot(None)
            )
            rows = session.execute(q).scalars().all()
            return list(rows)
    
    def get_unvisited_urls_by_config(self, config_id: int) -> List[str]:
        """Get all page URLs that exist but have no content (unvisited) for a config.
        
        These are pages that were discovered (inserted into DB) but not yet fetched.
        Useful for resuming crawls that were interrupted mid-discovery.
        
        Args:
            config_id: The crawler config ID
            
        Returns:
            List of page URLs with no page_content
        """
        with self.get_session() as session:
            q = select(DBPage.page_url).where(
                (DBPage.config_id == config_id) &
                (DBPage.page_content.is_(None))
            )
            rows = session.execute(q).scalars().all()
            return list(rows)

    def get_undiscovered_urls_by_depth(self, config_id: int, discovered_depth: int, limit: int = 1000) -> List[str]:
        """Get page URLs at a specific depth that haven't been fetched yet.
        
        Used for iterative depth-based crawling: fetch all pages at depth N,
        then all at depth N+1, etc.
        
        Args:
            config_id: The crawler config ID
            discovered_depth: The depth level to query
            limit: Maximum pages to return
            
        Returns:
            List of page URLs at the given depth with no page_content
        """
        with self.get_session() as session:
            q = select(DBPage.page_url).where(
                (DBPage.config_id == config_id) &
                (DBPage.discovered_depth == discovered_depth) &
                (DBPage.page_content.is_(None))
            ).limit(limit)
            rows = session.execute(q).scalars().all()
            return list(rows)

    def delete_pages_by_ids(self, page_ids: List[int]) -> int:
        """Delete pages by their IDs.
        
        Args:
            page_ids: List of page IDs to delete
            
        Returns:
            Number of pages deleted
        """
        if not page_ids:
            return 0
            
        with self.get_session() as session:
            stmt = delete(DBPage).where(DBPage.page_id.in_(page_ids))
            result = session.execute(stmt)
            session.commit()
            return result.rowcount

