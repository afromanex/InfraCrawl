import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScheduledCrawlJobRunner:
    """Runs a crawl for a given config path and tracks it in the registry + DB.

    This extracts the "execute a scheduled crawl" responsibility out of
    SchedulerService.
    """

    def __init__(
        self,
        *,
        config_provider,
        start_crawl_callback,
        crawl_registry,
        crawls_repo,
    ):
        self.config_provider = config_provider
        self.start_crawl_callback = start_crawl_callback
        self.crawl_registry = crawl_registry
        self.crawls_repo = crawls_repo

    def run(self, cfg_path: str) -> None:
        """Execute a scheduled crawl job for the given config path."""
        try:
            cfg = self.config_provider.get_config(cfg_path)
        except Exception as e:
            logger.warning("Scheduled config not found: %s - %s", cfg_path, e)
            return

        try:
            run_id: Optional[int] = None
            try:
                if self.crawls_repo is not None:
                    run_id = self.crawls_repo.create_run(cfg.config_id)
            except Exception:
                logger.exception("Could not create run record for %s", cfg_path)

            cid = None
            if self.crawl_registry is not None:
                cid = self.crawl_registry.start(config_name=cfg.config_path, config_id=cfg.config_id)

            stop_event = self.crawl_registry.get_stop_event(cid) if self.crawl_registry is not None else None

            try:
                # Call crawl callback directly (may block; scheduler runs worker thread).
                if stop_event is not None:
                    self.start_crawl_callback(cfg, stop_event)
                else:
                    self.start_crawl_callback(cfg)

                if cid and self.crawl_registry is not None:
                    self.crawl_registry.finish(cid, status="finished")

                if run_id is not None and self.crawls_repo is not None:
                    try:
                        self.crawls_repo.finish_run(run_id)
                    except Exception:
                        logger.exception("Could not finish run record for %s run=%s", cfg_path, run_id)

            except Exception as e:
                if cid and self.crawl_registry is not None:
                    self.crawl_registry.finish(cid, status="failed", error=str(e))

                if run_id is not None and self.crawls_repo is not None:
                    try:
                        self.crawls_repo.finish_run(run_id, exception=str(e))
                    except Exception:
                        logger.exception(
                            "Could not finish run record (failed) for %s run=%s",
                            cfg_path,
                            run_id,
                        )

                logger.exception("Scheduled crawl failed for %s", cfg_path)

        except Exception:
            logger.exception("Error running scheduled job for %s", cfg_path)
