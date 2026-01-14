from typing import Any, Optional, Protocol
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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
    # TODO: Unused parameters pages_repo and links_repo kept for "backwards compatibility" but never used. Remove them - simpler signature.
    def __init__(self, config_provider: ConfigProvider, start_crawl_callback, crawl_registry, pages_repo=None, links_repo=None):
        self.config_service = config_provider
        self.start_crawl_callback = start_crawl_callback
        self.crawl_registry = crawl_registry
        # optional repositories (backwards-compatible): some callers pass these
        self.pages_repo = pages_repo
        self.links_repo = links_repo
        self._sched: Optional[BackgroundScheduler] = None
        # TODO: Lazy import inside __init__ is unnecessarily clever. Import CrawlsRepository at top of file like everything else.
        # lazy-instantiate crawls repo so scheduler can record runs
        from infracrawl.repository.crawls import CrawlsRepository
        self.crawls_repo = CrawlsRepository()
        # config watcher interval (seconds). Can be overridden via env var
        try:
            self._config_watch_interval = int(os.getenv("INFRACRAWL_CONFIG_WATCH_INTERVAL", "60"))
        except Exception:
            logger.exception("Error parsing INFRACRAWL_CONFIG_WATCH_INTERVAL, using default 60")
            self._config_watch_interval = 60

    def start(self):
        if self._sched is not None:
            return
        self._sched = BackgroundScheduler()
        self._sched.start()
        logger.info("Scheduler started")
        self.load_and_schedule_all()
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
            full = self.config_service.get_config(db_cfg.config_path)
            if not full:
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
            if not cfg:
                logger.warning("Scheduled config not found: %s", cfg_path)
                return
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
