from infracrawl.services.crawler_config_parser import CrawlerConfigParser


def test_parse_requires_fetch_mode():
    parser = CrawlerConfigParser()
    cfg = parser.parse(config_path="configs/x.yml", data={"root_urls": ["http://example.com"]})
    assert cfg is None


def test_parse_uses_basename_for_config_path():
    parser = CrawlerConfigParser()
    cfg = parser.parse(
        config_path="/tmp/some/nested/test.yml",
        data={"fetch_mode": "http", "root_urls": ["http://example.com"]},
        config_id=123,
    )
    assert cfg is not None
    assert cfg.config_path == "test.yml"
    assert cfg.config_id == 123


def test_parse_defaults_root_urls_and_robots():
    parser = CrawlerConfigParser()
    cfg = parser.parse(
        config_path="a.yml",
        data={"fetch_mode": "http"},
    )
    assert cfg is not None
    assert cfg.root_urls == []
    assert cfg.robots is True
