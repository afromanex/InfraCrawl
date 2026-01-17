from infracrawl.repository.links import LinksRepository
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain import Link
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infracrawl.db.models import Base

def test_link_domain_roundtrip():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    pages_repo = PagesRepository(session_factory)
    links_repo = LinksRepository(session_factory)
    # Insert two pages to link between
    url1 = "https://example.com/a"
    url2 = "https://example.com/b"
    page1_id = pages_repo.ensure_page(url1)
    page2_id = pages_repo.ensure_page(url2)
    # Insert link
    link = Link(link_id=None, link_from_id=page1_id, link_to_id=page2_id, anchor_text="test anchor")
    links_repo.insert_link(link)
    # Fetch links and check
    links = links_repo.fetch_links()
    found = [link for link in links if link.link_from_id == page1_id and link.link_to_id == page2_id and link.anchor_text == "test anchor"]
    assert found, "Inserted link not found in fetch_links()"
