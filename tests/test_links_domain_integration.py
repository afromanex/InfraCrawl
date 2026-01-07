import pytest
from infracrawl.repository.links import LinksRepository
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain import Link

def test_link_domain_roundtrip():
    pages_repo = PagesRepository()
    links_repo = LinksRepository()
    # Insert two pages to link between
    url1 = "https://example.com/a"
    url2 = "https://example.com/b"
    page1_id = pages_repo.ensure_page(url1)
    page2_id = pages_repo.ensure_page(url2)
    # Insert link
    link = Link(link_id=None, link_from_id=page1_id, link_to_id=page2_id, anchor_text="test anchor")
    links_repo.insert_link(link)
    # Fetch links and check
    links = links_repo.fetch_links()
    found = [l for l in links if l.link_from_id == page1_id and l.link_to_id == page2_id and l.anchor_text == "test anchor"]
    assert found, "Inserted link not found in fetch_links()"
