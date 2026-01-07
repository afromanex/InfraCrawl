import pytest
from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.repository.pages import PagesRepository
from infracrawl.services.http_service import HttpService

class DummyHttp:
    def fetch(self, url):
        return 200, '<html><head><title>Hi</title></head><body><p>Hello <b>World</b></p></body></html>'


def test_plain_text_extracted_and_persisted(tmp_path):
    pages_repo = PagesRepository()
    svc = PageFetchPersistService(http_service=DummyHttp(), pages_repo=pages_repo)
    page = svc.persist('http://example.com', '200', '<html><body>Hi there</body></html>', '2026-01-01T00:00:00Z')
    assert page is not None
    # fetched page should have plain_text populated
    stored = pages_repo.get_page_by_url('http://example.com')
    assert stored is not None
    assert stored.plain_text is not None
    assert 'Hi there' in stored.plain_text
