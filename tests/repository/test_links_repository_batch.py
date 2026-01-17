from infracrawl.repository.links import LinksRepository
from infracrawl.repository.pages import PagesRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infracrawl.db.models import Base
from infracrawl.domain.link import Link
from infracrawl.domain.page import Page


def test_insert_links_batch_with_empty_list():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    repo = LinksRepository(session_factory)
    repo.insert_links_batch([])  # Should not raise


def test_insert_links_batch_inserts_multiple_links():
    # Create pages for links to reference
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    pages_repo = PagesRepository(session_factory)
    from_page = Page(page_url="http://example.com/batch-from")
    to_page1 = Page(page_url="http://example.com/batch-to1")
    to_page2 = Page(page_url="http://example.com/batch-to2")
    pages_repo.ensure_page(from_page)
    pages_repo.ensure_page(to_page1)
    pages_repo.ensure_page(to_page2)
    from_id = from_page.page_id
    to_id1 = to_page1.page_id
    to_id2 = to_page2.page_id
    
    repo = LinksRepository(session_factory)
    links = [
        Link(link_id=None, link_from_id=from_id, link_to_id=to_id1, anchor_text="batch-link1"),
        Link(link_id=None, link_from_id=from_id, link_to_id=to_id2, anchor_text="batch-link2"),
    ]
    repo.insert_links_batch(links)
    
    # Verify links were inserted
    fetched = repo.fetch_links()
    assert len(fetched) >= 2
    assert any(link.link_to_id == to_id1 and link.anchor_text == "batch-link1" for link in fetched)
    assert any(link.link_to_id == to_id2 and link.anchor_text == "batch-link2" for link in fetched)
