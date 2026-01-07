from infracrawl.services.content_review_service import ContentReviewService


def test_extract_links_ignores_missing_href():
    html = '<a>nohref</a><a href="/ok">ok</a>'
    svc = ContentReviewService()
    links = svc.extract_links('http://example.com', html)
    assert ('http://example.com/ok', 'ok') in links
    assert all(h != 'nohref' for (_, h) in links)


def test_extract_links_fragments_and_query_preserved():
    html = '<a href="/p?q=1#frag">X</a>'
    svc = ContentReviewService()
    links = svc.extract_links('http://example.com/base/', html)
    assert links == [('http://example.com/p?q=1#frag', 'X')]


def test_extract_links_mailto_and_javascript_included():
    html = '<a href="mailto:foo@example.com">mail</a><a href="javascript:void(0)">js</a>'
    svc = ContentReviewService()
    links = svc.extract_links('http://example.com', html)
    assert ('mailto:foo@example.com', 'mail') in links
    assert ('javascript:void(0)', 'js') in links


def test_extract_links_malformed_html_and_nested_text():
    html = '<a href="/a">A<a href="/b">B'
    svc = ContentReviewService()
    links = svc.extract_links('http://example.com', html)
    # both links should be present; BeautifulSoup combines adjacent text in malformed HTML
    assert ('http://example.com/a', 'AB') in links
    assert ('http://example.com/b', 'B') in links


def test_extract_links_anchor_text_strip_and_nested():
    html = '<a href="c"><span> Click <b>here</b> </span></a>'
    svc = ContentReviewService()
    links = svc.extract_links('http://example.com/root/', html)
    # BeautifulSoup get_text(strip=True) collapses spaces
    assert links == [('http://example.com/root/c', 'Clickhere')]
