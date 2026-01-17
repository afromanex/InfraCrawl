import threading

from infracrawl.services.crawl_registry import InMemoryCrawlRegistry


def test_registry_bounded_completed_retention():
    registry = InMemoryCrawlRegistry(max_completed_records=2)

    a = registry.start(config_name="a")
    b = registry.start(config_name="b")
    c = registry.start(config_name="c")

    assert registry.finish(a.crawl_id)
    assert registry.finish(b.crawl_id)
    assert registry.finish(c.crawl_id)

    assert registry.get(a.crawl_id) is None
    assert registry.get(b.crawl_id) is not None
    assert registry.get(c.crawl_id) is not None


def test_cancel_cleans_stop_event_mapping_but_sets_event():
    registry = InMemoryCrawlRegistry(max_completed_records=10)

    handle = registry.start(config_name="x")
    assert isinstance(handle.stop_event, threading.Event)

    assert registry.get_stop_event(handle.crawl_id) is handle.stop_event

    assert registry.cancel(handle.crawl_id)

    # The event object should be set for cooperative cancellation.
    assert handle.stop_event.is_set()

    # But the registry should not keep the mapping around indefinitely.
    assert registry.get_stop_event(handle.crawl_id) is None

    rec = registry.get(handle.crawl_id)
    assert rec is not None
    assert rec["status"] == "cancelled"
