from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CrawlRecord:
    id: str
    config_name: str
    config_id: Optional[int]
    status: str
    started_at: datetime
    last_seen: datetime
    finished_at: Optional[datetime] = None
    pages_fetched: int = 0
    links_found: int = 0
    current_url: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class CrawlHandle:
    crawl_id: str
    stop_event: threading.Event
