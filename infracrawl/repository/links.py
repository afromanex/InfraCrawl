from typing import Optional, List
from sqlalchemy import select
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

    def fetch_links(self, limit: Optional[int] = None) -> List[Link]:
        with self.get_session() as session:
            q = select(DBLink).order_by(DBLink.link_id)
            if limit:
                q = q.limit(limit)
            rows = session.execute(q).scalars().all()
            return [Link(
                link_id=l.link_id,
                link_from_id=l.link_from_id,
                link_to_id=l.link_to_id,
                anchor_text=l.anchor_text
            ) for l in rows]
