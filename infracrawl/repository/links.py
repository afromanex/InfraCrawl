from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from infracrawl.db.models import Link as DBLink
from infracrawl.domain import Link
from infracrawl.db.engine import make_engine


class LinksRepository:
    def __init__(self, engine=None):
        self.engine = engine or make_engine()

    def get_session(self) -> Session:
        return Session(self.engine)

    def insert_link(self, link: Link):
        with self.get_session() as session:
            db_link = DBLink(
                link_from_id=link.link_from_id,
                link_to_id=link.link_to_id,
                anchor_text=link.anchor_text
            )
            session.add(db_link)
            session.commit()

    def fetch_links(self, limit: Optional[int] = None, config_id: Optional[int] = None) -> List[Link]:
        with self.get_session() as session:
            # If config_id is provided, select links where either end references a page in that config
            if config_id is not None:
                # fetch page ids belonging to the config
                from infracrawl.db.models import Page as DBPage
                pid_q = select(DBPage.page_id).where(DBPage.config_id == config_id)
                page_ids = session.execute(pid_q).scalars().all()
                if not page_ids:
                    return []
                q = select(DBLink).where(or_(DBLink.link_from_id.in_(page_ids), DBLink.link_to_id.in_(page_ids))).order_by(DBLink.link_id)
            else:
                q = select(DBLink).order_by(DBLink.link_id)
            if limit:
                q = q.limit(limit)
            rows = session.execute(q).scalars().all()
            return [Link(
                link_id=row.link_id,
                link_from_id=row.link_from_id,
                link_to_id=row.link_to_id,
                anchor_text=row.anchor_text
            ) for row in rows]

    def delete_links_for_page_ids(self, page_ids: List[int]) -> int:
        """Delete any links referencing any of the provided page IDs. Returns number deleted."""
        if not page_ids:
            return 0
        with self.get_session() as session:
            q = session.query(DBLink).filter(or_(DBLink.link_from_id.in_(page_ids), DBLink.link_to_id.in_(page_ids)))
            deleted = q.delete(synchronize_session=False)
            session.commit()
            return deleted
