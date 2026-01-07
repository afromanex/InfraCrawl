from typing import Optional
from datetime import datetime


class CrawlerConfig:
    def __init__(self, config_id: int, config_path: str, root_urls=None, max_depth=None, robots=True, refresh_days=None, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.config_id = config_id
        self.config_path = config_path
        self.root_urls = root_urls or []
        self.max_depth = max_depth
        self.robots = robots
        self.refresh_days = refresh_days
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<CrawlerConfig id={self.config_id} path={self.config_path}>"
