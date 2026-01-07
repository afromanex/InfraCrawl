from typing import List, Optional
from datetime import datetime

class CrawlerConfig:
    def __init__(self, config_id: int, name: str, root_urls: List[str], max_depth: int, robots: bool = True, refresh_days: Optional[int] = None, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.config_id = config_id
        self.name = name
        self.root_urls = root_urls
        self.max_depth = max_depth
        self.robots = robots
        self.refresh_days = refresh_days
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self):
        return f"<CrawlerConfig id={self.config_id} name={self.name}>"
