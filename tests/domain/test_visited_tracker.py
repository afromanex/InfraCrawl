from infracrawl.domain.visited_tracker import VisitedTracker


def test_url_not_visited_initially():
    tracker = VisitedTracker()
    assert not tracker.is_visited("https://example.com")


def test_marking_url_makes_it_visited():
    tracker = VisitedTracker()
    tracker.mark("https://example.com")
    assert tracker.is_visited("https://example.com")


def test_different_urls_tracked_independently():
    tracker = VisitedTracker()
    tracker.mark("https://example.com")
    assert tracker.is_visited("https://example.com")
    assert not tracker.is_visited("https://other.com")


def test_marking_same_url_twice_is_idempotent():
    tracker = VisitedTracker()
    tracker.mark("https://example.com")
    tracker.mark("https://example.com")
    assert tracker.is_visited("https://example.com")
