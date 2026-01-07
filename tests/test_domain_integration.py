import pytest
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain import CrawlerConfig

def test_config_domain_roundtrip():
    repo = ConfigsRepository()
    config = CrawlerConfig(
        config_id=None,
        name="pytest-config",
        root_urls=["https://example.com/"],
        max_depth=1,
        robots=True,
        refresh_days=5
    )
    # Insert
    config_id = repo.upsert_config(config)
    assert isinstance(config_id, int)
    # Fetch by name
    loaded = repo.get_config("pytest-config")
    assert loaded is not None
    assert loaded.name == config.name
    assert loaded.root_urls == config.root_urls
    # List
    configs = repo.list_configs()
    assert any(c.name == "pytest-config" for c in configs)
    # Delete
    repo.delete_config("pytest-config")
    assert repo.get_config("pytest-config") is None
