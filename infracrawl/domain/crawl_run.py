from typing import Optional
from datetime import datetime


class CrawlRun:
    def __init__(self, run_id: int, config_id: Optional[int], config_path: Optional[str], start_timestamp: datetime, end_timestamp: Optional[datetime], exception: Optional[str]):
        self.run_id = run_id
        self.config_id = config_id
        self.config_path = config_path
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.exception = exception

    def __repr__(self):
        return (
            f"<CrawlRun id={self.run_id} config={self.config_path} "
            f"start={self.start_timestamp} end={self.end_timestamp}>"
        )
