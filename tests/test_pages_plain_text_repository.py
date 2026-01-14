from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.page import Page


def test_upsert_and_fetch_plain_text():
    repo = PagesRepository()
    url = 'http://repo-test.local/page'
    # ensure clean
    repo.ensure_page(url)
    page_obj = Page(
        page_id=None,
        page_url=url,
        page_content='<html><body>Repo Test</body></html>',
        plain_text='Repo Test',
        http_status=200,
        fetched_at='2026-01-01T00:00:00Z'
    )
    p = repo.upsert_page(page_obj)
    assert p is not None
    fetched = repo.get_page_by_url(url)
    assert fetched is not None
    assert fetched.plain_text == 'Repo Test'
    # get_page_by_url already confirms plain_text persisted; no further global assertions to avoid test interference
