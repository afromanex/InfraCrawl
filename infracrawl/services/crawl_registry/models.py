from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, List, Optional


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
    recent_urls: Deque[str] = field(default_factory=lambda: deque(maxlen=20))

    def get_recent_urls(self) -> List[str]:
        """Return recent URLs as a list (most recent first)."""
        return list(reversed(self.recent_urls))


@dataclass(frozen=True)
class CrawlHandle:
    crawl_id: str
    stop_event: threading.Event
