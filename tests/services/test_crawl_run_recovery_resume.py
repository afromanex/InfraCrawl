import types
from infracrawl.services.crawl_run_recovery import CrawlRunRecovery


class DummyConfig:
    def __init__(self, config_id: int, config_path: str, resume_on_application_restart: bool = False):
        self.config_id = config_id
        self.config_path = config_path
        self.resume_on_application_restart = resume_on_application_restart


class DummyConfigProvider:
    def __init__(self, configs):
        self._configs = configs

    def list_configs(self):
        return self._configs
    
    def get_config(self, config_path: str):
        """Return the matching config from the list."""
        for cfg in self._configs:
            if cfg.config_path == config_path:
                return cfg
        raise FileNotFoundError(f"Config {config_path} not found")


class DummyCrawlsRepo:
    def __init__(self, counts_by_config_id, has_incomplete_map=None):
        self.counts_by_config_id = counts_by_config_id
        self.has_incomplete_map = has_incomplete_map or {}
        self.mark_calls = []
        self.incomplete_checks = []

    def mark_incomplete_runs(self, config_id: int, within_seconds=None, message=None) -> int:
        self.mark_calls.append((config_id, within_seconds, message))
        return int(self.counts_by_config_id.get(config_id, 0))

    def has_incomplete_runs(self, config_id: int, within_seconds=None) -> bool:
        self.incomplete_checks.append((config_id, within_seconds))
        return self.has_incomplete_map.get(config_id, False)


def test_recovery_invokes_resume_callback_when_enabled_and_no_incomplete_runs():
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=True),
    ])
    repo = DummyCrawlsRepo({1: 1}, has_incomplete_map={1: False})

    calls = []
    def resume_cb(cfg):
        calls.append(cfg.config_path)

    r = CrawlRunRecovery(config_provider=provider, crawls_repo=repo, within_seconds=None)
    # monkey patch: inject resume callback temporarily for test
    r._resume_callback = resume_cb  # type: ignore[attr-defined]

    r.recover()

    # Should mark incomplete and then resume since none are currently incomplete
    assert repo.mark_calls == [(1, None, "job found incomplete on startup")]
    assert repo.incomplete_checks == [(1, None)]
    assert calls == ["a.yml"]


def test_recovery_does_not_resume_when_incomplete_runs_exist():
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=True),
    ])
    repo = DummyCrawlsRepo({1: 1}, has_incomplete_map={1: True})

    calls = []
    def resume_cb(cfg):
        calls.append(cfg.config_path)

    r = CrawlRunRecovery(config_provider=provider, crawls_repo=repo, within_seconds=None)
    r._resume_callback = resume_cb  # type: ignore[attr-defined]

    r.recover()

    assert repo.mark_calls == [(1, None, "job found incomplete on startup")]
    assert repo.incomplete_checks == [(1, None)]
    # Should skip resume because DB indicates an active/incomplete run already
    assert calls == []


def test_recovery_does_not_resume_when_flag_disabled():
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=False),
    ])
    repo = DummyCrawlsRepo({1: 1}, has_incomplete_map={1: False})

    calls = []
    def resume_cb(cfg):
        calls.append(cfg.config_path)

    r = CrawlRunRecovery(config_provider=provider, crawls_repo=repo, within_seconds=None)
    r._resume_callback = resume_cb  # type: ignore[attr-defined]

    r.recover()

    assert repo.mark_calls == [(1, None, "job found incomplete on startup")]
    # No check needed because resume flag is false
    assert calls == []
