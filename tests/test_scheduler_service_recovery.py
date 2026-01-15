import os

from infracrawl.services.scheduler_service import SchedulerService


class DummyConfig:
    def __init__(self, config_id: int, config_path: str):
        self.config_id = config_id
        self.config_path = config_path


class DummyConfigProvider:
    def __init__(self, configs):
        self._configs = configs

    def list_configs(self):
        return self._configs

    def get_config(self, config_path: str):
        raise NotImplementedError()

    def sync_configs_with_disk(self) -> None:
        raise NotImplementedError()


class DummyCrawlsRepo:
    def __init__(self, counts_by_config_id):
        self.counts_by_config_id = counts_by_config_id
        self.calls = []

    def mark_incomplete_runs(self, config_id: int, within_seconds=None, message=None) -> int:
        self.calls.append((config_id, within_seconds, message))
        return int(self.counts_by_config_id.get(config_id, 0))


class DummyScheduler:
    def __init__(self):
        self.added = []

    def add_job(self, func, trigger=None, id=None, replace_existing=None):
        self.added.append({
            "func": func,
            "trigger": trigger,
            "id": id,
            "replace_existing": replace_existing,
        })


def test_recovery_mark_mode_marks_incomplete_runs():
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml"),
        DummyConfig(2, "b.yml"),
    ])
    crawls_repo = DummyCrawlsRepo({1: 2, 2: 0})

    svc = SchedulerService(
        provider,
        start_crawl_callback=lambda *a, **k: None,
        crawl_registry=None,
        crawls_repo=crawls_repo,
        recovery_mode="mark",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
    )
    svc._sched = DummyScheduler()

    svc._recover_incomplete_runs_on_startup()

    assert crawls_repo.calls == [
        (1, None, "startup recovery"),
        (2, None, "startup recovery"),
    ]
    assert svc._sched.added == []


def test_recovery_restart_mode_schedules_restart_for_configs_with_incomplete():
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml"),
        DummyConfig(2, "b.yml"),
    ])
    crawls_repo = DummyCrawlsRepo({1: 1, 2: 0})

    svc = SchedulerService(
        provider,
        start_crawl_callback=lambda *a, **k: None,
        crawl_registry=None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=3600,
        recovery_message="startup recovery",
    )
    sched = DummyScheduler()
    svc._sched = sched

    svc._recover_incomplete_runs_on_startup()

    assert crawls_repo.calls == [
        (1, 3600, "startup recovery"),
        (2, 3600, "startup recovery"),
    ]

    assert len(sched.added) == 1
    assert sched.added[0]["id"] == "recovery:a.yml"
    assert sched.added[0]["replace_existing"] is True


def test_recovery_off_mode_does_nothing():
    provider = DummyConfigProvider([DummyConfig(1, "a.yml")])
    crawls_repo = DummyCrawlsRepo({1: 1})

    svc = SchedulerService(
        provider,
        start_crawl_callback=lambda *a, **k: None,
        crawl_registry=None,
        crawls_repo=crawls_repo,
        recovery_mode="off",
    )
    svc._sched = DummyScheduler()

    svc._recover_incomplete_runs_on_startup()

    assert crawls_repo.calls == []
    assert svc._sched.added == []
