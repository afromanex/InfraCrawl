import os

from infracrawl.services.config_file_store import ConfigFileStore


def test_list_config_files_filters_yaml_extensions(tmp_path):
    (tmp_path / "a.yml").write_text("fetch_mode: http\nroot_urls: []\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("fetch_mode: http\nroot_urls: []\n", encoding="utf-8")
    (tmp_path / "c.txt").write_text("nope", encoding="utf-8")

    store = ConfigFileStore(configs_dir=str(tmp_path))
    files = store.list_config_files()

    assert set(files) == {"a.yml", "b.yaml"}


def test_load_yaml_dict_missing_file_returns_none(tmp_path):
    store = ConfigFileStore(configs_dir=str(tmp_path))
    assert store.load_yaml_dict("missing.yml") is None


def test_load_yaml_dict_non_dict_returns_none(tmp_path):
    (tmp_path / "list.yml").write_text("- a\n- b\n", encoding="utf-8")
    store = ConfigFileStore(configs_dir=str(tmp_path))
    assert store.load_yaml_dict("list.yml") is None


def test_load_yaml_dict_invalid_yaml_returns_none(tmp_path):
    # Invalid YAML should be treated as missing/invalid config, not crash.
    (tmp_path / "bad.yml").write_text(": this is not valid yaml", encoding="utf-8")
    store = ConfigFileStore(configs_dir=str(tmp_path))
    assert store.load_yaml_dict("bad.yml") is None


def test_load_yaml_dict_dict_is_returned(tmp_path):
    (tmp_path / "ok.yml").write_text("fetch_mode: http\nroot_urls: []\n", encoding="utf-8")
    store = ConfigFileStore(configs_dir=str(tmp_path))
    data = store.load_yaml_dict("ok.yml")
    assert isinstance(data, dict)
    assert data["fetch_mode"] == "http"


def test_read_raw_yaml_missing_returns_none(tmp_path):
    store = ConfigFileStore(configs_dir=str(tmp_path))
    assert store.read_raw_yaml("missing.yml") is None


def test_resolve_path_uses_configs_dir_for_relative(tmp_path):
    (tmp_path / "ok.yml").write_text("fetch_mode: http\n", encoding="utf-8")
    store = ConfigFileStore(configs_dir=str(tmp_path))

    data = store.load_yaml_dict("ok.yml")
    assert data == {"fetch_mode": "http"}


def test_resolve_path_allows_absolute(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    cfg = other / "abs.yml"
    cfg.write_text("fetch_mode: http\n", encoding="utf-8")

    store = ConfigFileStore(configs_dir=str(tmp_path))
    data = store.load_yaml_dict(str(cfg))
    assert data == {"fetch_mode": "http"}
