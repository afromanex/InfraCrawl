import logging
from typing import Optional

from infracrawl.repository.crawls import CrawlsRepository
from infracrawl.services.protocols import ConfigProvider

logger = logging.getLogger(__name__)


class CrawlRunRecovery:
    """Best-effort recovery for incomplete crawl runs left in the DB.

    This extracts startup recovery policy out of SchedulerService.
    """

    def __init__(
        self,
        *,
        config_provider: ConfigProvider,
        crawls_repo: CrawlsRepository,
        within_seconds: Optional[int],
    ) -> None:
        self.config_provider = config_provider
        self.crawls_repo = crawls_repo
        self.within_seconds = within_seconds

    def recover(self) -> None:
        """Mark incomplete crawl runs as complete."""
        if self.crawls_repo is None:
            return

        logger.info("Recovery: scanning configs for incomplete runs")
        configs = self.config_provider.list_configs()

        for db_cfg in configs:
            cfg_id: Optional[int] = getattr(db_cfg, "config_id", None)
            cfg_path: Optional[str] = getattr(db_cfg, "config_path", None)
            if cfg_id is None or not cfg_path:
                continue

            try:
                count: int = self.crawls_repo.mark_incomplete_runs(
                    cfg_id,
                    within_seconds=self.within_seconds,
                    message="job found incomplete on startup",
                )
            except Exception:
                logger.exception("Failed marking incomplete runs for config %s", cfg_path)
                continue

            if count <= 0:
                continue

            logger.info("Recovered %s incomplete run(s) for %s", count, cfg_path)

            # Always load full config to check resume flag (may have been updated since DB last synced)
            resume: bool = False
            try:
                full_cfg = self.config_provider.get_config(cfg_path)
                resume = bool(getattr(full_cfg, "resume_on_application_restart", False))
                logger.info("Resume flag for %s: %s", cfg_path, resume)
            except Exception:
                logger.exception("Recovery: could not load full config for %s to check resume flag", cfg_path)
                resume = False
            
            if resume:
                # Skip restart if there are already incomplete (running) runs for this config
                try:
                    has_incomplete = self.crawls_repo.has_incomplete_runs(cfg_id, within_seconds=self.within_seconds)
                    logger.info("Has incomplete runs for %s (id=%s): %s", cfg_path, cfg_id, has_incomplete)
                    if has_incomplete:
                        logger.info(
                            "Skipping recovery restart for %s (resume_on_application_restart enabled, incomplete runs exist)",
                            cfg_path,
                        )
                        continue
                except Exception:
                    logger.exception("Error checking incomplete runs for %s", cfg_path)

                # If a resume callback is provided (wired by the scheduler/container), invoke it
                resume_cb = getattr(self, "_resume_callback", None)
                logger.info("Resume callback available for %s: %s", cfg_path, callable(resume_cb))
                if callable(resume_cb):
                    try:
                        logger.info(
                            "Recovery: initiating resume for config %s (id=%s)",
                            cfg_path,
                            cfg_id,
                        )
                        resume_cb(db_cfg)
                        continue
                    except Exception:
                        logger.exception("Error invoking resume callback for %s", cfg_path)
            else:
                logger.info("Resume disabled for %s, will mark as complete only", cfg_path)

            # Fallback: Log that job should be restarted if no callback available
            logger.warning(
                "Job for config %s (id=%s) should be restarted. Restart mechanism still needs to be implemented.",
                cfg_path,
                cfg_id,
            )
