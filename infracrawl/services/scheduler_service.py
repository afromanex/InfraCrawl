from typing import Any, Optional
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from infracrawl.services.crawl_run_recovery import CrawlRunRecovery
from infracrawl.services.scheduled_crawl_job_runner import ScheduledCrawlJobRunner
from infracrawl.services.protocols import ConfigProvider
from infracrawl.repository.pages import PagesRepository

logger = logging.getLogger(__name__)


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
        session_factory,
        start_crawl_callback,
        crawls_repo,
        *,
        resume_session_factory=None,
        config_watch_interval_seconds: int = 60,
        recovery_mode: str = "restart",
        recovery_within_seconds: Optional[int] = None,
        recovery_message: str = "job found incomplete on startup",
        pages_repo=None,
    ):
        self.config_service = config_provider
        self.session_factory = session_factory
        self.start_crawl_callback = start_crawl_callback
        self.crawls_repo = crawls_repo
        self._sched: Optional[BackgroundScheduler] = None
        self._config_watch_interval = int(config_watch_interval_seconds)
        self._recovery_mode = (recovery_mode or "restart").strip().lower()
        self._recovery_within_seconds = recovery_within_seconds
        self._recovery_message = recovery_message

        # Build pages repo if not provided and we have a session factory
        self.pages_repo = pages_repo or (PagesRepository(self.session_factory) if self.session_factory else None)

        self._job_runner = ScheduledCrawlJobRunner(
            config_provider=self.config_service,
            session_factory=self.session_factory,
            resume_session_factory=resume_session_factory,
            start_crawl_callback=self.start_crawl_callback,
            crawls_repo=self.crawls_repo,
        )
        self._recovery = CrawlRunRecovery(
            config_provider=self.config_service,
            crawls_repo=self.crawls_repo,
            within_seconds=self._recovery_within_seconds,
            pages_repo=self.pages_repo,
        )
        # Wire resume callback so recovery can trigger an actual resumed job
        try:
            self._recovery._resume_callback = lambda cfg: self._job_runner.run_config_resume(cfg)  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Failed wiring resume callback into recovery")

    def start(self):
        if self._sched is not None:
            return
        self._sched = BackgroundScheduler()
        self._sched.start()
        logger.info("Scheduler started")
        self.load_and_schedule_all()
        
        # Schedule recovery as a one-time background job to avoid blocking startup
        try:
            self._sched.add_job(
                self._recover_incomplete_runs_on_startup,
                trigger='date',  # run once immediately
                id="startup_recovery",
                replace_existing=True,
            )
            logger.info("Scheduled startup recovery job")
        except Exception:
            logger.exception("Could not schedule startup recovery")
        
        # schedule periodic config watcher to keep DB in sync with disk
        try:
            # use an interval trigger to periodically scan configs
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

        Kept as a SchedulerService method for backwards compatibility and tests,
        but delegated to CrawlRunRecovery.
        """
        mode_norm = (self._recovery_mode or "restart").strip().lower()
        if mode_norm in {"off", "0", "false", "none"}:
            return
        
        logger.info("Checking for jobs to restart")
        self._recovery.recover()

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
        
        logger.info("Loading scheduled jobs from configs")
        
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
        # HTTP `/crawl` endpoint.
        self._job_runner.run(cfg_path)

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
