from infracrawl.services.content_review_service import ContentReviewService

def test_extract_links_basic():
    html = '<html><body><a href="/foo">Foo</a><a href="http://bar.com">Bar</a></body></html>'
    svc = ContentReviewService()
    links = svc.extract_links('http://example.com', html)
    assert ('http://example.com/foo', 'Foo') in links
    assert ('http://bar.com', 'Bar') in links
    assert len(links) == 2
