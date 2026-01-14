from typing import Optional, Any
from datetime import datetime

# TODO: ISP - CrawlerConfig combines DB fields (config_id, created_at, updated_at) + domain fields (root_urls, max_depth). Concrete risk: crawler needs config but gets DB timestamps it ignores; DB repo must handle domain fields. Minimal fix: split into CrawlerConfigMetadata (id/timestamps) + CrawlerConfigData (roots/depth); compose where needed.
class CrawlerConfig:
    def __init__(
        self,
        config_id: int,
        config_path: str,
        root_urls=None,
        max_depth=None,
        robots=True,
        refresh_days=None,
        schedule: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.config_id = config_id
        self.config_path = config_path
        self.root_urls = root_urls or []
        self.max_depth = max_depth
        self.robots = robots
        self.refresh_days = refresh_days
        # `schedule` is an optional object parsed from the YAML config; it is
        # not persisted to the DB in the current implementation. Acceptable
        # forms include a cron string ("0 2 * * *"), or a dict with
        # {"type": "cron", ...} or {"type": "interval", ...}.
        self.schedule = schedule
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<CrawlerConfig id={self.config_id} path={self.config_path} schedule={self.schedule}>"
