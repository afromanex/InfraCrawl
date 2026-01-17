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

        self.run_config(cfg)

    def run_config(self, cfg) -> None:
        """Execute a crawl job for an already-loaded config object.

        This is useful for API paths that validate/load config synchronously
        and then enqueue the actual crawl work as a background task.
        """

        cfg_path = getattr(cfg, "config_path", None)
        try:
            run_id: Optional[int] = None
            try:
                if self.crawls_repo is not None:
                    run_id = self.crawls_repo.create_run(cfg.config_id)
            except Exception:
                logger.exception("Could not create run record for %s", cfg_path)

            cid = None
            stop_event = None
            if self.crawl_registry is not None:
                handle = self.crawl_registry.start(config_name=cfg.config_path, config_id=cfg.config_id)
                cid = handle.crawl_id
                stop_event = handle.stop_event

            try:
                # Wrap the crawl callback to inject crawl_id
                def wrapped_crawl(config, se=None):
                    return self.start_crawl_callback(config, se, crawl_id=cid)
                
                # Call crawl callback directly (may block; scheduler runs worker thread).
                if stop_event is not None:
                    wrapped_crawl(cfg, stop_event)
                else:
                    wrapped_crawl(cfg)

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

                logger.exception("Crawl job failed for %s", cfg_path)

        except Exception:
            logger.exception("Error running crawl job for %s", cfg_path)
