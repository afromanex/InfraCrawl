from infracrawl.services.crawl_registry import InMemoryCrawlRegistry


def test_recent_urls_order_and_size_cap():
    registry = InMemoryCrawlRegistry(max_completed_records=10)
    handle = registry.start(config_name="cfg")

    # Record 25 URLs; the deque should cap at 20, most recent first
    for i in range(25):
        url = f"https://example.com/page/{i}"
        assert registry.update(handle.crawl_id, current_url=url)

    recent = registry.get_recent_urls(handle.crawl_id)
    assert recent is not None
    assert len(recent) == 20
    # Most recent should be the last ones recorded, in reverse order
    assert recent[0] == "https://example.com/page/24"
    assert recent[-1] == "https://example.com/page/5"


def test_recent_urls_for_unknown_crawl_returns_none():
    registry = InMemoryCrawlRegistry(max_completed_records=10)
    assert registry.get_recent_urls("missing") is None
