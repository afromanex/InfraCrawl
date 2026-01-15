from typing import Any, Optional, Protocol
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)


class ConfigProvider(Protocol):
    """Minimal interface for config access - ensures Interface Segregation Principle.
    
    SchedulerService only needs these 3 methods, not the full ConfigService.
    This allows easier testing with minimal mocks and reduces coupling.
    """
    def list_configs(self): ...
    def get_config(self, config_path: str): ...
    def sync_configs_with_disk(self) -> None: ...


def _parse_schedule(schedule: Any):
    """Return an APScheduler CronTrigger from a cron schedule string.

    Accepts cron strings like '0 2 * * *' (crontab format).
    Returns None if schedule is invalid or cannot be parsed.
    """
    if schedule is None:
        return None
    if isinstance(schedule, str):
        try:
            return CronTrigger.from_crontab(schedule)
        except Exception:
            logger.exception("Error parsing cron schedule: %s", schedule)
            return None
    logger.warning("Unsupported schedule format: %s (only cron strings supported)", type(schedule))
    return None


class SchedulerService:
    def __init__(
        self,
        config_provider: ConfigProvider,
        start_crawl_callback,
        crawl_registry,
        crawls_repo,
        *,
        config_watch_interval_seconds: int = 60,
        recovery_mode: str = "restart",
        recovery_within_seconds: Optional[int] = None,
        recovery_message: str = "job found incomplete on startup",
    ):
        self.config_service = config_provider
        self.start_crawl_callback = start_crawl_callback
        self.crawl_registry = crawl_registry
        self.crawls_repo = crawls_repo
        self._sched: Optional[BackgroundScheduler] = None
        self._config_watch_interval = int(config_watch_interval_seconds)
        self._recovery_mode = (recovery_mode or "restart").strip().lower()
        self._recovery_within_seconds = recovery_within_seconds
        self._recovery_message = recovery_message

    def start(self):
        if self._sched is not None:
            return
        self._sched = BackgroundScheduler()
        self._sched.start()
        logger.info("Scheduler started")
        self.load_and_schedule_all()
        self._recover_incomplete_runs_on_startup()
        # schedule periodic config watcher to keep DB in sync with disk
        try:
            # TODO: IntervalTrigger already imported at top - duplicate import inside method is unnecessary.
            # use an interval trigger to periodically scan configs
            from apscheduler.triggers.interval import IntervalTrigger

            self._sched.add_job(
                self._run_config_watcher,
                trigger=IntervalTrigger(seconds=self._config_watch_interval),
                id="config_watcher",
                replace_existing=True,
            )
            logger.info("Scheduled config watcher every %s seconds", self._config_watch_interval)
        except Exception:
            logger.exception("Could not schedule config watcher")

    def _recover_incomplete_runs_on_startup(self):
        """Best-effort recovery for service disruptions.

        Level 1 recovery: mark any DB crawl runs left incomplete (no end_timestamp)
        as finished with a clear exception message.

        Optionally, restart those crawls from root by scheduling an immediate job.
        """
        if self.crawls_repo is None:
            return
        if not self._sched:
            return

        if self._recovery_mode in {"off", "0", "false", "none"}:
            return
        within_seconds = self._recovery_within_seconds
        message = self._recovery_message

        try:
            configs = self.config_service.list_configs()
        except Exception:
            logger.exception("Could not list configs for recovery")
            return

        for db_cfg in configs:
            cfg_id = getattr(db_cfg, "config_id", None)
            cfg_path = getattr(db_cfg, "config_path", None)
            if cfg_id is None or not cfg_path:
                continue

            try:
                count = self.crawls_repo.mark_incomplete_runs(cfg_id, within_seconds=within_seconds, message=message)
            except Exception:
                logger.exception("Failed marking incomplete runs for config %s", cfg_path)
                continue

            if count <= 0:
                continue

            logger.info("Recovered %s incomplete run(s) for %s", count, cfg_path)

            if self._recovery_mode == "restart":
                try:
                    job_id = f"recovery:{cfg_path}"
                    self._sched.add_job(
                        lambda p=cfg_path: self._execute_scheduled_crawl(p),
                        trigger=DateTrigger(run_date=datetime.now(timezone.utc)),
                        id=job_id,
                        replace_existing=True,
                    )
                    logger.info("Scheduled recovery restart for %s", cfg_path)
                except Exception:
                    logger.exception("Failed scheduling recovery restart for %s", cfg_path)

    def shutdown(self, wait: bool = True):
        if not self._sched:
            return
        try:
            self._sched.shutdown(wait=wait)
            logger.info("Scheduler shut down")
        finally:
            self._sched = None

    def load_and_schedule_all(self):
        """Load schedules from YAML-backed configs and schedule crawl jobs."""
        if not self._sched:
            logger.warning("Scheduler not started; cannot load schedules")
            return
        # Remove existing schedule jobs we previously added
        for job in list(self._sched.get_jobs()):
            if job.id.startswith("schedule:"):
                self._sched.remove_job(job.id)

        db_configs = self.config_service.list_configs()
        for db_cfg in db_configs:
            try:
                full = self.config_service.get_config(db_cfg.config_path)
            except Exception as e:
                logger.warning("Could not load config %s: %s", db_cfg.config_path, e)
                continue
            trig = _parse_schedule(full.schedule)
            if trig is None:
                continue
            job_id = f"schedule:{full.config_path}"

            # CLAUDE: "Closure captures cfg_path" means without default arg, ALL jobs would use last loop value. Default arg fixes it: def _job(cfg_path=full.config_path) captures current iteration.
            try:
                self._sched.add_job(
                    lambda cfg_path=full.config_path: self._execute_scheduled_crawl(cfg_path),
                    trigger=trig,
                    id=job_id,
                    replace_existing=True
                )
                logger.info("Scheduled job %s -> %s", job_id, full.schedule)
            except Exception:
                logger.exception("Could not schedule job for %s", full.config_path)

    def _execute_scheduled_crawl(self, cfg_path: str):
        """Execute a scheduled crawl job for the given config path."""
        # When APScheduler calls this job, we perform the same logic as the
        # HTTP `/crawl` endpoint: register in registry and call the
        # crawler callback cooperatively with stop event.
        try:
            cfg = self.config_service.get_config(cfg_path)
        except Exception as e:
            logger.warning("Scheduled config not found: %s - %s", cfg_path, e)
            return
        
        try:
            # create DB run record
            run_id = None
            try:
                run_id = self.crawls_repo.create_run(cfg.config_id)
            except Exception:
                logger.exception("Could not create run record for %s", cfg_path)

            cid = None
            if self.crawl_registry is not None:
                cid = self.crawl_registry.start(config_name=cfg.config_path, config_id=cfg.config_id)
            stop_event = self.crawl_registry.get_stop_event(cid) if self.crawl_registry is not None else None
            try:
                # call crawler directly (this may block until finished);
                # APSScheduler runs this in a worker thread so it's fine.
                self.start_crawl_callback(cfg, stop_event) if stop_event is not None else self.start_crawl_callback(cfg)
                if cid and self.crawl_registry is not None:
                    self.crawl_registry.finish(cid, status="finished")
                # finish DB run record
                if run_id is not None:
                    try:
                        self.crawls_repo.finish_run(run_id)
                    except Exception:
                        logger.exception("Could not finish run record for %s run=%s", cfg_path, run_id)
            except Exception as e:
                if cid and self.crawl_registry is not None:
                    self.crawl_registry.finish(cid, status="failed", error=str(e))
                # record exception in DB run
                if run_id is not None:
                    try:
                        self.crawls_repo.finish_run(run_id, exception=str(e))
                    except Exception:
                        logger.exception("Could not finish run record (failed) for %s run=%s", cfg_path, run_id)
                logger.exception("Scheduled crawl failed for %s", cfg_path)
        except Exception:
            logger.exception("Error running scheduled job for %s", cfg_path)

    def _run_config_watcher(self):
        """Periodic job: sync configs on disk with DB and reload scheduled crawl jobs."""
        try:
            logger.info("Config watcher: syncing configs with disk")
            try:
                self.config_service.sync_configs_with_disk()
            except Exception:
                logger.exception("Error syncing configs with disk")
            # reload scheduled crawl jobs after sync
            try:
                self.load_and_schedule_all()
            except Exception:
                logger.exception("Error reloading scheduled crawl jobs after config sync")
        except Exception:
            logger.exception("Unhandled error in config watcher")
