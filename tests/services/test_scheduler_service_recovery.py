import os
import logging
import threading
import time
from infracrawl.services.scheduler_service import SchedulerService


class DummyConfig:
    def __init__(self, config_id: int, config_path: str, resume_on_application_restart: bool = True, schedule=None):
        self.config_id = config_id
        self.config_path = config_path
        self.resume_on_application_restart = resume_on_application_restart
        self.schedule = schedule  # Optional schedule for job scheduling tests


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


class DummyPagesRepo:
    def __init__(self, unvisited_map=None):
        self.unvisited_map = unvisited_map or {}
        self.calls = []

    def has_unvisited_urls_by_config(self, config_id: int) -> bool:
        self.calls.append(config_id)
        return self.unvisited_map.get(config_id, False)


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
    
    def get_jobs(self):
        return []


def test_recovery_mark_mode_marks_incomplete_runs():
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml"),
        DummyConfig(2, "b.yml"),
    ])
    crawls_repo = DummyCrawlsRepo({1: 2, 2: 0})
    pages_repo = DummyPagesRepo({1: False, 2: False})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="mark",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
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
    pages_repo = DummyPagesRepo({1: False, 2: False})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=3600,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
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


def test_recovery_logs_startup_and_per_config(caplog):
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=False),
    ])
    crawls_repo = DummyCrawlsRepo({1: 1})
    pages_repo = DummyPagesRepo({1: False})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
    )
    svc._sched = DummyScheduler()

    caplog.set_level(logging.INFO)
    svc._recover_incomplete_runs_on_startup()

    # Expect high-level startup log and recovery scanning
    scheduler_logs = " ".join(r.message for r in caplog.records if r.name.endswith("scheduler_service"))
    recovery_logs = " ".join(r.message for r in caplog.records if r.name.endswith("crawl_run_recovery"))

    assert "Checking for jobs to restart" in scheduler_logs
    assert "Recovery: scanning configs for incomplete runs" in recovery_logs
    assert "Recovery: marked 1 incomplete run(s) for a.yml" in recovery_logs
    # Since resume flag is False, expect fallback restart guidance log
    assert "Job for config a.yml (id=1) should be restarted" in recovery_logs


def test_recovery_logs_initiating_resume(caplog):
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=True),
    ])
    crawls_repo = DummyCrawlsRepo({1: 1}, has_incomplete_map={1: False})
    pages_repo = DummyPagesRepo({1: False})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
    )
    svc._sched = DummyScheduler()

    caplog.set_level(logging.INFO)
    svc._recover_incomplete_runs_on_startup()

    recovery_logs = " ".join(r.message for r in caplog.records if r.name.endswith("crawl_run_recovery"))
    assert "Recovery: dispatching resume for config a.yml (id=1) asynchronously" in recovery_logs


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
    pages_repo = DummyPagesRepo({1: False})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
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
    pages_repo = DummyPagesRepo({1: False})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
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


def test_recovery_resume_dispatches_async_and_does_not_block():
    """Resume callbacks should be dispatched without blocking other configs."""
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=True),
        DummyConfig(2, "b.yml", resume_on_application_restart=True),
    ])
    crawls_repo = DummyCrawlsRepo({1: 1, 2: 1}, has_incomplete_map={1: False, 2: False})
    pages_repo = DummyPagesRepo({1: True, 2: True})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
    )
    svc._sched = DummyScheduler()

    calls = []
    ready = threading.Event()

    def blocking_resume(cfg):
        calls.append(cfg.config_id)
        ready.wait(timeout=0.5)  # simulate long-running resume

    # Wire the blocking callback to simulate real resume behavior
    svc._recovery._resume_callback = blocking_resume

    start = time.time()
    svc._recover_incomplete_runs_on_startup()
    duration = time.time() - start

    # Allow executor to start threads
    time.sleep(0.05)

    # Even though callbacks block, both should be dispatched without delaying recover
    assert duration < 0.2
    assert set(calls) == {1, 2}
    # Unblock threads to avoid dangling waits
    ready.set()


def test_recovery_resumes_when_unvisited_pages_exist_even_if_no_incomplete_runs(caplog):
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml", resume_on_application_restart=True),
        DummyConfig(2, "b.yml", resume_on_application_restart=True),
    ])
    # Config 1 has incomplete runs; config 2 has none but has unvisited pages.
    crawls_repo = DummyCrawlsRepo({1: 1, 2: 0}, has_incomplete_map={1: False, 2: False})
    pages_repo = DummyPagesRepo({1: False, 2: True})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="restart",
        recovery_within_seconds=None,
        recovery_message="startup recovery",
        pages_repo=pages_repo,
    )
    svc._sched = DummyScheduler()

    calls = []

    class ImmediateExecutor:
        def submit(self, fn, *args, **kwargs):
            return fn(*args, **kwargs)

    svc._recovery._resume_callback = lambda cfg: calls.append(cfg.config_id)
    svc._recovery._resume_executor = ImmediateExecutor()

    caplog.set_level(logging.INFO)
    svc._recover_incomplete_runs_on_startup()

    # Both configs should be resumed: cfg1 via incomplete run, cfg2 via unvisited pages
    assert set(calls) == {1, 2}
    recovery_logs = " ".join(r.message for r in caplog.records if r.name.endswith("crawl_run_recovery"))
    assert "unvisited pages exist for b.yml" in recovery_logs
    assert "dispatching resume for config b.yml" in recovery_logs

def test_load_and_schedule_logs_loading_message(caplog):
    provider = DummyConfigProvider([
        DummyConfig(1, "a.yml"),
    ])
    crawls_repo = DummyCrawlsRepo({})

    svc = SchedulerService(
        provider,
        None,  # session_factory
        start_crawl_callback=lambda *a, **k: None,
        crawls_repo=crawls_repo,
        recovery_mode="off",  # Disable recovery to isolate scheduling logs
    )
    sched = DummyScheduler()
    svc._sched = sched

    caplog.set_level(logging.INFO)
    svc.load_and_schedule_all()

    scheduler_logs = " ".join(r.message for r in caplog.records if r.name.endswith("scheduler_service"))
    assert "Loading scheduled jobs from configs" in scheduler_logs