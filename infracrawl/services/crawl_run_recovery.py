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

            # Check config's resume_on_application_restart setting (from full YAML config)
            resume: bool = getattr(db_cfg, "resume_on_application_restart", False)
            if not resume:
                # Fallback to full config load to read resume flag when DB row lacks it
                try:
                    full_cfg = self.config_provider.get_config(cfg_path)
                    resume = bool(getattr(full_cfg, "resume_on_application_restart", False))
                except Exception:
                    # If a specific config can't be loaded, don't crash recovery – just log and continue.
                    logger.exception("Recovery: could not load full config for %s to check resume flag", cfg_path)
                    resume = False
            if resume:
                # Skip restart if there are already incomplete (running) runs for this config
                try:
                    if self.crawls_repo.has_incomplete_runs(cfg_id, within_seconds=self.within_seconds):
                        logger.info(
                            "Skipping recovery restart for %s (resume_on_application_restart enabled, incomplete runs exist)",
                            cfg_path,
                        )
                        continue
                except Exception:
                    logger.exception("Error checking incomplete runs for %s", cfg_path)

                # If a resume callback is provided (wired by the scheduler/container), invoke it
                resume_cb = getattr(self, "_resume_callback", None)
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

            # Fallback: Log that job should be restarted if no callback available
            logger.warning(
                "Job for config %s (id=%s) should be restarted. Restart mechanism still needs to be implemented.",
                cfg_path,
                cfg_id,
            )
