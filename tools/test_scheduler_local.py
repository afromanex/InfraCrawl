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


logging.basicConfig(level=logging.INFO)


def dummy_crawl(cfg, stop_event=None):
    print(f"dummy_crawl invoked for {cfg.config_path}")


def main():
    cfg_service = ConfigService()
    # ensure configs are loaded
    cfg_service.sync_configs_with_disk()

    registry = InMemoryCrawlRegistry()
    sched = SchedulerService(cfg_service, dummy_crawl, registry)
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
