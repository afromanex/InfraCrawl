from infracrawl.repository.pages import PagesRepository


def test_upsert_and_fetch_plain_text():
    repo = PagesRepository()
    url = 'http://repo-test.local/page'
    # ensure clean
    repo.ensure_page(url)
    p = repo.upsert_page(url, '<html><body>Repo Test</body></html>', 200, '2026-01-01T00:00:00Z', plain_text='Repo Test')
    assert p is not None
    fetched = repo.get_page_by_url(url)
    assert fetched is not None
    assert fetched.plain_text == 'Repo Test'
    # get_page_by_url already confirms plain_text persisted; no further global assertions to avoid test interference
