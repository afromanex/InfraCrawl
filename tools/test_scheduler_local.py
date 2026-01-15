import time
import logging
import os
import sys

# Ensure repo root is on sys.path so `infracrawl` package imports resolve when
# running the script directly.
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from infracrawl.services.config_service import ConfigService
from infracrawl.services.crawl_registry import InMemoryCrawlRegistry
from infracrawl.services.scheduler_service import SchedulerService
from infracrawl import config as env
from infracrawl.repository.configs import ConfigsRepository
from sqlalchemy.orm import sessionmaker
from infracrawl.db.engine import make_engine


logging.basicConfig(level=logging.INFO)


def dummy_crawl(cfg, stop_event=None):
    print(f"dummy_crawl invoked for {cfg.config_path}")


def main():
    session_factory = sessionmaker(bind=make_engine(), future=True)
    cfg_repo = ConfigsRepository(session_factory)
    cfg_service = ConfigService(cfg_repo)
    # ensure configs are loaded
    cfg_service.sync_configs_with_disk()

    registry = InMemoryCrawlRegistry()
    from infracrawl.repository.crawls import CrawlsRepository
    crawls_repo = CrawlsRepository(session_factory)
    sched = SchedulerService(
        cfg_service,
        dummy_crawl,
        registry,
        crawls_repo,
        config_watch_interval_seconds=env.get_int_env("INFRACRAWL_CONFIG_WATCH_INTERVAL", 60),
        recovery_mode=env.get_str_env("INFRACRAWL_RECOVERY_MODE", "restart").strip().lower(),
        recovery_within_seconds=env.get_optional_int_env("INFRACRAWL_RECOVERY_WITHIN_SECONDS"),
        recovery_message=env.get_str_env("INFRACRAWL_RECOVERY_MESSAGE", "job found incomplete on startup"),
    )
    sched.start()

    # give the scheduler a moment to add jobs
    time.sleep(1)

    jobs = sched._sched.get_jobs() if sched._sched else []
    print(f"Scheduled jobs: {len(jobs)}")
    for j in jobs:
        print(j.id, j.trigger)

    sched.shutdown()


if __name__ == '__main__':
    main()
