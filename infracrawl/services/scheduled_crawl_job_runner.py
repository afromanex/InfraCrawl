import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScheduledCrawlJobRunner:
    """Runs a crawl for a given config path and tracks it in the registry + DB.

    This extracts the "execute a scheduled crawl" responsibility out of
    SchedulerService. Uses a CrawlSessionFactory to create tracked sessions.
    """

    def __init__(
        self,
        *,
        config_provider,
        session_factory,
        start_crawl_callback,
        crawl_registry,
        crawls_repo,
    ):
        self.config_provider = config_provider
        self.session_factory = session_factory
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

            # Create session via factory (handles registry.start() if registry exists)
            session = self.session_factory.create(cfg)

            try:
                # Call crawl callback with session (may block; scheduler runs worker thread).
                self.start_crawl_callback(session)

                # Finish registry tracking if session was tracked
                if session.crawl_id and self.crawl_registry is not None:
                    self.crawl_registry.finish(session.crawl_id, status="finished")

                if run_id is not None and self.crawls_repo is not None:
                    try:
                        self.crawls_repo.finish_run(run_id)
                    except Exception:
                        logger.exception("Could not finish run record for %s run=%s", cfg_path, run_id)

            except Exception as e:
                # Finish registry tracking with failure status
                if session.crawl_id and self.crawl_registry is not None:
                    self.crawl_registry.finish(session.crawl_id, status="failed", error=str(e))

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
