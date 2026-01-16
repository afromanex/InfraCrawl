from __future__ import annotations

from dataclasses import dataclass

from infracrawl.services.config_syncer import ConfigSyncer


@dataclass
class _DbCfg:
    config_path: str


@dataclass
class _UpsertResult:
    config_id: int


class _FakeRepo:
    def __init__(self, existing_paths: list[str] | None = None):
        self._existing_paths = list(existing_paths or [])
        self.upserted: list[str] = []
        self.deleted: list[str] = []

    def upsert_config(self, config_obj):
        self.upserted.append(config_obj.config_path)
        if config_obj.config_path not in self._existing_paths:
            self._existing_paths.append(config_obj.config_path)
        return _UpsertResult(config_id=1)

    def list_configs(self):
        return [_DbCfg(p) for p in self._existing_paths]

    def delete_config(self, config_path: str):
        self.deleted.append(config_path)
        if config_path in self._existing_paths:
            self._existing_paths.remove(config_path)


class _FakeFileStore:
    def __init__(self, *, files: dict[str, object]):
        self._files = files

    def list_config_files(self):
        return list(self._files.keys())

    def load_yaml_dict(self, fname: str):
        return self._files[fname]


@dataclass
class _ParsedCfg:
    config_path: str


class _FakeParser:
    def parse(self, *, config_path: str, data: dict):
        if not isinstance(data, dict):
            return None
        if data.get("fetch_mode") is None:
            return None
        return _ParsedCfg(config_path=config_path)


def test_sync_upserts_valid_and_deletes_orphans():
    file_store = _FakeFileStore(
        files={
            "a.yml": {"fetch_mode": "http"},
            "b.yml": {"fetch_mode": "http"},
            "bad.yml": ["not-a-dict"],
            "missing_fetch_mode.yml": {"root_urls": []},
        }
    )
    repo = _FakeRepo(existing_paths=["old.yml", "a.yml"])
    parser = _FakeParser()

    syncer = ConfigSyncer(file_store=file_store, configs_repo=repo, parser=parser)
    syncer.sync()

    # Valid files upserted
    assert set(repo.upserted) == {"a.yml", "b.yml"}

    # Orphan removed
    assert repo.deleted == ["old.yml"]
