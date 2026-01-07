import pytest
from infracrawl.repository.configs import ConfigsRepository
from infracrawl.domain import CrawlerConfig

def test_config_domain_roundtrip():
    repo = ConfigsRepository()
    config = CrawlerConfig(
        config_id=None,
        config_path="pytest-config.yml",
        root_urls=["https://example.com/"],
        max_depth=1,
        robots=True,
        refresh_days=5
    )
    # Insert
    config_id = repo.upsert_config(config)
    assert isinstance(config_id, int)
    # Fetch by config_path
    loaded = repo.get_config("pytest-config.yml")
    assert loaded is not None
    assert loaded.config_path == config.config_path
    # Simulate loading full config from YAML using config_path
    import os, yaml
    config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")
    yaml_path = os.path.join(config_dir, loaded.config_path)
    if os.path.isfile(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["root_urls"] == config.root_urls
    else:
        # If the file doesn't exist, just check the config_path is correct
        assert loaded.config_path == config.config_path
    # List
    configs = repo.list_configs()
    assert any(c.config_path == "pytest-config.yml" for c in configs)
    # Delete (by config_path)
    repo.delete_config("pytest-config.yml")
    assert repo.get_config("pytest-config.yml") is None
