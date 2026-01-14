from infracrawl.services.page_fetch_persist_service import PageFetchPersistService
from infracrawl.repository.pages import PagesRepository
from infracrawl.services.http_response import HttpResponse

class StaticHttp:
    def fetch(self, url):
        return HttpResponse(200, '<html><body><h1>Title</h1><p>Content for integration test.</p></body></html>')


def test_crawl_persists_plain_text():
    pages = PagesRepository()
    svc = PageFetchPersistService(http_service=StaticHttp(), pages_repo=pages)
    page = svc.fetch_and_persist('http://integration.test/', None)
    assert page is not None
    stored = pages.get_page_by_url('http://integration.test/')
    assert stored is not None
    assert 'Content for integration test' in (stored.plain_text or '')
