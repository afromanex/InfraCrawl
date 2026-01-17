from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.page import Page
from sqlalchemy.orm import sessionmaker
from infracrawl.db.engine import make_engine


def test_crawl_persists_plain_text():
    session_factory = sessionmaker(bind=make_engine(), future=True)
    pages = PagesRepository(session_factory)
    svc = PageFetchPersistService(http_service=None, pages_repo=pages)
    page = Page(page_url='http://integration.test/', page_content='<html><body><h1>Title</h1><p>Content for integration test.</p></body></html>', http_status=200)
    success = svc.extract_and_persist(page)
    assert success is True
    assert page.page_id is not None
    stored = pages.get_page_by_url('http://integration.test/')
    assert stored is not None
    assert 'Content for integration test' in (stored.plain_text or '')
