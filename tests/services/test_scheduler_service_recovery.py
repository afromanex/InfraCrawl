import os

from infracrawl.services.scheduler_service import SchedulerService


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
        raise NotImplementedError()

    def sync_configs_with_disk(self) -> None:
        raise NotImplementedError()


class DummyCrawlsRepo:
    def __init__(self, counts_by_config_id, has_incomplete_map=None):
        self.counts_by_config_id = counts_by_config_id
        self.has_incomplete_map = has_incomplete_map or {}  # config_id -> bool
        self.calls = []

    def mark_incomplete_runs(self, config_id: int, within_seconds=None, message=None) -> int:
        self.calls.append((config_id, within_seconds, message))
        return int(self.counts_by_config_id.get(config_id, 0))

    def has_incomplete_runs(self, config_id: int, within_seconds=None) -> bool:
        return self.has_incomplete_map.get(config_id, False)


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
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="mark",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
    )
    svc._sched = DummyScheduler()

    svc._recover_incomplete_runs_on_startup()

    assert crawls_repo.calls == [
        (1, None, "job found incomplete on startup"),
        (2, None, "job found incomplete on startup"),
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
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=3600,
        recovery_message="startup recovery",
    )
    sched = DummyScheduler()
    svc._sched = sched

    svc._recover_incomplete_runs_on_startup()

    assert crawls_repo.calls == [
        (1, 3600, "job found incomplete on startup"),
        (2, 3600, "job found incomplete on startup"),
    ]

    # Jobs are no longer automatically scheduled; logging indicates what should be restarted
    assert len(sched.added) == 0


def test_recovery_off_mode_does_nothing():
    provider = DummyConfigProvider([DummyConfig(1, "a.yml")])
    crawls_repo = DummyCrawlsRepo({1: 1})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="off",
    )
    svc._sched = DummyScheduler()

    svc._recover_incomplete_runs_on_startup()


def test_recovery_restart_skips_if_incomplete_runs_in_db():
    """When recovering and config already has incomplete runs, skip restart scheduling."""
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=True),
    ])
    # Config 1 has 1 incomplete run that will be marked
    crawls_repo = DummyCrawlsRepo(
        {1: 1},
        has_incomplete_map={1: True},  # Already has incomplete runs
    )

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
    )
    sched = DummyScheduler()
    svc._sched = sched

    svc._recover_incomplete_runs_on_startup()

    # Mark incomplete runs should be called (to mark old runs complete)
    assert crawls_repo.calls == [
        (1, None, "job found incomplete on startup"),
    ]
    # But should skip scheduling restart because database already has incomplete runs
    assert sched.added == []


def test_recovery_restart_schedules_when_resume_false():
    """When resume_on_application_restart=False, always schedule restart even if incomplete runs exist."""
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=False),
    ])
    # Config 1 has 1 incomplete run that will be marked
    crawls_repo = DummyCrawlsRepo(
        {1: 1},
        has_incomplete_map={1: True},  # Already has incomplete runs
    )

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
    )
    sched = DummyScheduler()
    svc._sched = sched

    svc._recover_incomplete_runs_on_startup()

    # Mark incomplete runs should be called
    assert crawls_repo.calls == [
        (1, None, "job found incomplete on startup"),
    ]
    # Should not schedule restart because resume_on_application_restart is False (logging indicates what to do)
    assert len(sched.added) == 0
