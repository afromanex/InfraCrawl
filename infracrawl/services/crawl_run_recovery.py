import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)


class CrawlRunRecovery:
    """Best-effort recovery for incomplete crawl runs left in the DB.

    This extracts startup recovery policy out of SchedulerService.
    """

    def __init__(
        self,
        *,
        config_provider,
        crawls_repo,
        schedule_restart_fn,
    ):
        self.config_provider = config_provider
        self.crawls_repo = crawls_repo
        self.schedule_restart_fn = schedule_restart_fn

    def recover(
        self,
        *,
        sched,
        mode: str,
        within_seconds: Optional[int],
        message: str,
    ) -> None:
        if self.crawls_repo is None:
            return
        if not sched:
            return

        mode_norm = (mode or "restart").strip().lower()
        if mode_norm in {"off", "0", "false", "none"}:
            return

        try:
            configs = self.config_provider.list_configs()
        except Exception:
            logger.exception("Could not list configs for recovery")
            return

        for db_cfg in configs:
            cfg_id = getattr(db_cfg, "config_id", None)
            cfg_path = getattr(db_cfg, "config_path", None)
            if cfg_id is None or not cfg_path:
                continue

            try:
                count = self.crawls_repo.mark_incomplete_runs(
                    cfg_id,
                    within_seconds=within_seconds,
                    message=message,
                )
            except Exception:
                logger.exception("Failed marking incomplete runs for config %s", cfg_path)
                continue

            if count <= 0:
                continue

            logger.info("Recovered %s incomplete run(s) for %s", count, cfg_path)

            if mode_norm == "restart":
                try:
                    job_id = f"recovery:{cfg_path}"
                    sched.add_job(
                        lambda p=cfg_path: self.schedule_restart_fn(p),
                        trigger=DateTrigger(run_date=datetime.now(timezone.utc)),
                        id=job_id,
                        replace_existing=True,
                    )
                    logger.info("Scheduled recovery restart for %s", cfg_path)
                except Exception:
                    logger.exception("Failed scheduling recovery restart for %s", cfg_path)
