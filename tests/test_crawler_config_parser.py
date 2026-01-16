from infracrawl.services.crawler_config_parser import CrawlerConfigParser


def test_parse_requires_fetch_section():
    parser = CrawlerConfigParser()
    cfg = parser.parse(config_path="configs/x.yml", data={"root_urls": ["http://example.com"]})
    assert cfg is None


def test_parse_uses_basename_for_config_path():
    parser = CrawlerConfigParser()
    cfg = parser.parse(
        config_path="/tmp/some/nested/test.yml",
        data={"fetch": {"mode": "http"}, "root_urls": ["http://example.com"]},
        config_id=123,
    )
    assert cfg is not None
    assert cfg.config_path == "test.yml"
    assert cfg.config_id == 123


def test_parse_defaults_root_urls_and_robots():
    parser = CrawlerConfigParser()
    cfg = parser.parse(
        config_path="a.yml",
        data={"fetch": {"mode": "http"}},
    )
    assert cfg is not None
    assert cfg.root_urls == []
    assert cfg.robots is True


def test_parse_with_nested_fetch_options():
    """Test parsing YAML with mode-specific options nested under fetch."""
    parser = CrawlerConfigParser()
    data = {
        "root_urls": ["https://example.com"],
        "max_depth": 3,
        "robots": True,
        "refresh_days": 7,
        "fetch": {
            "mode": "headless_chromium",
            "headless_chromium": {
                "wait_until": "networkidle",
                "timeout_ms": 15000,
            },
        },
    }
    cfg = parser.parse(config_path="test.yml", data=data, config_id=1)
    assert cfg is not None
    assert cfg.fetch_mode == "headless_chromium"
    assert cfg.fetch_options == {"mode": "headless_chromium", "headless_chromium": {"wait_until": "networkidle", "timeout_ms": 15000}}
    assert cfg.headless_options == {"wait_until": "networkidle", "timeout_ms": 15000}


def test_parse_with_flat_fetch_mode_returns_none():
    """Test that old flat format is no longer supported."""
    parser = CrawlerConfigParser()
    data = {
        "root_urls": ["https://example.com"],
        "fetch_mode": "http",
    }
    cfg = parser.parse(config_path="test.yml", data=data, config_id=2)
    # Old flat format should return None (no fetch section found)
    assert cfg is None


def test_nested_format_with_only_fetch_section():
    """Test nested format with mode-specific section (no mode-specific options)."""
    parser = CrawlerConfigParser()
    data = {
        "root_urls": ["https://example.com"],
        "fetch": {
            "mode": "http",
        },
    }
    cfg = parser.parse(config_path="test.yml", data=data, config_id=3)
    assert cfg is not None
    assert cfg.fetch_mode == "http"
    assert cfg.fetch_options == {"mode": "http"}
    assert cfg.headless_options is None
