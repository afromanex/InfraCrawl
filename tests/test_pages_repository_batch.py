from infracrawl.repository.pages import PagesRepository


def test_ensure_pages_batch_returns_empty_for_no_urls():
    repo = PagesRepository()
    result = repo.ensure_pages_batch([])
    assert result == {}


def test_ensure_pages_batch_creates_new_pages():
    repo = PagesRepository()
    urls = ["http://example.com/batch-a", "http://example.com/batch-b"]
    result = repo.ensure_pages_batch(urls)
    assert len(result) == 2
    assert all(url in result for url in urls)
    assert all(isinstance(page_id, int) for page_id in result.values())


def test_ensure_pages_batch_returns_existing_page_ids():
    repo = PagesRepository()
    url = "http://example.com/batch-existing"
    # Create page first
    existing_id = repo.ensure_page(url)
    # Batch should return same ID
    result = repo.ensure_pages_batch([url])
    assert result[url] == existing_id


def test_ensure_pages_batch_mixes_new_and_existing():
    repo = PagesRepository()
    existing_url = "http://example.com/batch-mix-existing"
    new_url = "http://example.com/batch-mix-new"
    existing_id = repo.ensure_page(existing_url)
    
    result = repo.ensure_pages_batch([existing_url, new_url])
    assert result[existing_url] == existing_id
    assert new_url in result
    assert result[new_url] != existing_id
