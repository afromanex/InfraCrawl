import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ScheduledCrawlJobRunner:
    """Runs a crawl for a given config path and tracks it in the registry + DB.

    This extracts the "execute a scheduled crawl" responsibility out of
    SchedulerService. Uses a CrawlSessionFactory to create tracked sessions.
    The session handles all registry tracking operations via finish_tracking().
    """

    def __init__(
        self,
        *,
        config_provider,
        session_factory,
        resume_session_factory=None,
        start_crawl_callback,
        crawls_repo,
    ):
        self.config_provider = config_provider
        self.session_factory = session_factory
        self.resume_session_factory = resume_session_factory
        self.start_crawl_callback = start_crawl_callback
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

                # Finish registry tracking via session
                session.finish_tracking(status="finished")

                if run_id is not None and self.crawls_repo is not None:
                    try:
                        self.crawls_repo.finish_run(run_id)
                    except Exception:
                        logger.exception("Could not finish run record for %s run=%s", cfg_path, run_id)

            except Exception as e:
                # Finish registry tracking via session with failure status
                session.finish_tracking(status="failed", error=str(e))

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

    def run_config_resume(self, cfg) -> None:
        """Execute a resumed crawl job for an already-loaded config object.

        Uses the resume session factory to pre-populate visited state so the
        crawl continues where it left off.
        """
        cfg_path = getattr(cfg, "config_path", None)
        try:
            # Always load full config from provider to ensure we have root_urls,
            # depth, and other YAML-backed fields (recovery passes a DB row summary).
            if cfg_path:
                cfg = self.config_provider.get_config(cfg_path)
            else:
                logger.warning("Resume called without config_path; cannot load full config")
        except Exception as e:
            logger.warning("Resume: config not found: %s - %s", cfg_path, e)
            return
        logger.info("Starting resumed crawl job for %s", cfg_path)
        try:
            run_id: Optional[int] = None
            try:
                if self.crawls_repo is not None:
                    run_id = self.crawls_repo.create_run(cfg.config_id)
            except Exception:
                logger.exception("Could not create run record for %s", cfg_path)

            if self.resume_session_factory is None:
                logger.warning("Resume session factory not configured; falling back to normal run for %s", cfg_path)
                return self.run_config(cfg)

            # Create resumed session via factory (handles registry.start())
            session = self.resume_session_factory.rebuild(cfg)

            try:
                # Execute crawl with resumed session
                self.start_crawl_callback(session)

                # Finish registry tracking via session
                session.finish_tracking(status="finished")

                if run_id is not None and self.crawls_repo is not None:
                    try:
                        self.crawls_repo.finish_run(run_id)
                    except Exception:
                        logger.exception("Could not finish run record for %s run=%s", cfg_path, run_id)
                logger.info("Resumed crawl job finished for %s", cfg_path)

            except Exception as e:
                # Finish registry tracking via session with failure status
                session.finish_tracking(status="failed", error=str(e))

                if run_id is not None and self.crawls_repo is not None:
                    try:
                        self.crawls_repo.finish_run(run_id, exception=str(e))
                    except Exception:
                        logger.exception(
                            "Could not finish run record (failed) for %s run=%s",
                            cfg_path,
                            run_id,
                        )

                logger.exception("Resumed crawl job failed for %s", cfg_path)

        except Exception:
            logger.exception("Error running resumed crawl job for %s", cfg_path)
