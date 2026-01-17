from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.page import Page
from sqlalchemy.orm import sessionmaker
from infracrawl.db.engine import make_engine


def test_ensure_pages_batch_returns_empty_for_no_urls():
    repo = PagesRepository(sessionmaker(bind=make_engine(), future=True))
    result = repo.ensure_pages_batch([])
    assert result == {}


def test_ensure_pages_batch_creates_new_pages():
    repo = PagesRepository(sessionmaker(bind=make_engine(), future=True))
    urls = ["http://example.com/batch-a", "http://example.com/batch-b"]
    result = repo.ensure_pages_batch(urls)
    assert len(result) == 2
    assert all(url in result for url in urls)
    assert all(isinstance(page_id, int) for page_id in result.values())


def test_ensure_pages_batch_returns_existing_page_ids():
    repo = PagesRepository(sessionmaker(bind=make_engine(), future=True))
    url = "http://example.com/batch-existing"
    # Create page first
    existing_page = Page(page_url=url)
    repo.ensure_page(existing_page)
    existing_id = existing_page.page_id
    # Batch should return same ID
    result = repo.ensure_pages_batch([url])
    assert result[url] == existing_id


def test_ensure_pages_batch_mixes_new_and_existing():
    repo = PagesRepository(sessionmaker(bind=make_engine(), future=True))
    existing_url = "http://example.com/batch-mix-existing"
    new_url = "http://example.com/batch-mix-new"
    existing_page = Page(page_url=existing_url)
    repo.ensure_page(existing_page)
    existing_id = existing_page.page_id
    
    result = repo.ensure_pages_batch([existing_url, new_url])
    assert result[existing_url] == existing_id
    assert new_url in result
    assert result[new_url] != existing_id
