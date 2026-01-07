from typing import Any, Dict, Optional
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def _parse_schedule(schedule: Any):
    """Return an APScheduler trigger from a schedule object.

    Accepts:
    - a cron string like '0 2 * * *' (crontab)
    - a dict with 'type': 'cron' and cron fields (minute, hour, day, month, day_of_week)
    - a dict with 'type': 'interval' and interval fields (seconds, minutes, hours, days)
    """
    if schedule is None:
        return None
    # cron string
    if isinstance(schedule, str):
        try:
            return CronTrigger.from_crontab(schedule)
        except Exception:
            return None
    if isinstance(schedule, dict):
        t = schedule.get("type")
        if t == "cron":
            args = {k: v for k, v in schedule.items() if k != "type"}
            try:
                return CronTrigger(**args)
            except Exception:
                return None
        if t == "interval":
            args = {k: v for k, v in schedule.items() if k != "type"}
            try:
                return IntervalTrigger(**args)
            except Exception:
                return None
    return None


class SchedulerService:
    def __init__(self, config_service, start_crawl_callback, crawl_registry):
        self.config_service = config_service
        self.start_crawl_callback = start_crawl_callback
        self.crawl_registry = crawl_registry
        self._sched: Optional[BackgroundScheduler] = None
        # lazy-instantiate crawls repo so scheduler can record runs
        from infracrawl.repository.crawls import CrawlsRepository
        self.crawls_repo = CrawlsRepository()

    def start(self):
        if self._sched is not None:
            return
        self._sched = BackgroundScheduler()
        self._sched.start()
        logger.info("Scheduler started")
        self.load_and_schedule_all()

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

            def _job(cfg_path=full.config_path):
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

            try:
                self._sched.add_job(_job, trigger=trig, id=job_id, replace_existing=True)
                logger.info("Scheduled job %s -> %s", job_id, full.schedule)
            except Exception:
                logger.exception("Could not schedule job for %s", full.config_path)
