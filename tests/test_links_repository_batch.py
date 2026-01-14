from infracrawl.repository.links import LinksRepository
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.link import Link


def test_insert_links_batch_with_empty_list():
    repo = LinksRepository()
    repo.insert_links_batch([])  # Should not raise


def test_insert_links_batch_inserts_multiple_links():
    # Create pages for links to reference
    pages_repo = PagesRepository()
    from_id = pages_repo.ensure_page("http://example.com/batch-from")
    to_id1 = pages_repo.ensure_page("http://example.com/batch-to1")
    to_id2 = pages_repo.ensure_page("http://example.com/batch-to2")
    
    repo = LinksRepository()
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
