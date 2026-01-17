from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.page import Page
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infracrawl.db.models import Base
import hashlib

class DummyHttp:
    def fetch(self, url):
        return 200, '<html><head><title>Hi</title></head><body><p>Hello <b>World</b></p></body></html>'


def test_plain_text_extracted_and_persisted(tmp_path):
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    pages_repo = PagesRepository(session_factory)
    svc = PageFetchPersistService(http_service=DummyHttp(), pages_repo=pages_repo)
    page = Page(page_url='http://example.com', page_content='<html><body>Hi there</body></html>', http_status=200)
    success = svc.extract_and_persist(page)
    assert success is True
    assert page.page_id is not None
    assert page.plain_text is not None
    assert 'Hi there' in page.plain_text
    # Verify it was persisted
    stored = pages_repo.get_page_by_url('http://example.com')
    assert stored is not None
    assert stored.plain_text is not None
    assert 'Hi there' in stored.plain_text


def test_filtered_plain_text_removes_boilerplate():
    """Test that filtered_plain_text removes navigation, headers, footers, and other non-content elements."""
    html = '''
    <html>
    <head><title>Test Page</title></head>
    <body>
    <header>Site Header</header>
    <nav>Navigation Menu</nav>
    <main>
    <h1>Main Content</h1>
    <p>This is the main content that should be kept.</p>
    </main>
    <aside class="sidebar">Sidebar content</aside>
    <footer>Site Footer</footer>
    </body>
    </html>
    '''
    
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    pages_repo = PagesRepository(session_factory)
    svc = PageFetchPersistService(http_service=DummyHttp(), pages_repo=pages_repo)
    page = Page(page_url='http://test.com', page_content=html, http_status=200)
    success = svc.extract_and_persist(page)
    assert success is True
    
    stored = pages_repo.get_page_by_url('http://test.com')
    assert stored is not None
    
    # Plain text should include everything
    assert stored.plain_text is not None
    assert 'Site Header' in stored.plain_text
    assert 'Navigation Menu' in stored.plain_text
    assert 'Main Content' in stored.plain_text
    assert 'This is the main content that should be kept.' in stored.plain_text
    assert 'Sidebar content' in stored.plain_text
    assert 'Site Footer' in stored.plain_text
    
    # Filtered plain text should only include main content
    assert stored.filtered_plain_text is not None
    assert 'Main Content' in stored.filtered_plain_text
    assert 'This is the main content that should be kept.' in stored.filtered_plain_text
    
    # Should NOT include navigation, header, footer, or sidebar
    assert 'Site Header' not in stored.filtered_plain_text
    assert 'Navigation Menu' not in stored.filtered_plain_text
    assert 'Sidebar content' not in stored.filtered_plain_text
    assert 'Site Footer' not in stored.filtered_plain_text


def test_content_hash_persisted_from_filtered_plain_text():
    html = '<html><body><h1>Hello</h1><div>World</div></body></html>'
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    pages_repo = PagesRepository(session_factory)
    svc = PageFetchPersistService(http_service=DummyHttp(), pages_repo=pages_repo)

    # Persist with provided HTML
    page = Page(page_url='http://hash.test', page_content=html, http_status=200)
    success = svc.extract_and_persist(page)
    assert success is True

    # Compute expected SHA-256 of filtered text (newline-separated get_text)
    # The HtmlTextExtractor returns filtered text with newlines between blocks.
    # We recompute expected by reusing the stored filtered_plain_text for determinism.
    stored = pages_repo.get_page_by_url('http://hash.test')
    assert stored is not None
    assert stored.filtered_plain_text is not None
    expected = hashlib.sha256(stored.filtered_plain_text.encode('utf-8')).hexdigest()

    # Repository should expose the same hash via the domain model once implemented
    # This assertion will fail until content_hash is added to DB and domain mapping.
    assert getattr(stored, 'content_hash', None) == expected


def test_upsert_deduplicates_by_config_and_content_hash():
    """Same content under same config should not create a duplicate page."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    pages_repo = PagesRepository(session_factory)
    svc = PageFetchPersistService(http_service=DummyHttp(), pages_repo=pages_repo)

    # Persist first URL with config_id=1
    html = '<html><body><main>Unique Content</main></body></html>'
    page1 = Page(page_url='http://example.com/page1', page_content=html, http_status=200, config_id=1)
    success1 = svc.extract_and_persist(page1)
    assert success1 is True
    
    # Persist same content under different URL but same config_id
    page2 = Page(page_url='http://example.com/page2', page_content=html, http_status=200, config_id=1)
    success2 = svc.extract_and_persist(page2)
    assert success2 is True
    
    repo_page1 = page1
    repo_page2 = page2
    
    # Both should have the same content_hash
    assert repo_page1.content_hash == repo_page2.content_hash
    
    # Second upsert should detect the duplicate and return the existing page without creating a new entry
    # We verify by checking if only one page exists in DB for this content_hash under config_id=1
    from sqlalchemy import select
    from infracrawl.db.models import Page as DBPage
    with pages_repo.get_session() as session:
        existing = session.execute(
            select(DBPage).where(
                (DBPage.content_hash == repo_page1.content_hash) & (DBPage.config_id == 1)
            )
        ).scalars().all()
    # Should be only 1 page, not 2
    assert len(existing) == 1
