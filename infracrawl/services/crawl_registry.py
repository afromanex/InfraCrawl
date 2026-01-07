from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional


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


class InMemoryCrawlRegistry:
    """Thread-safe in-memory registry for active and recent crawls.

    This is intentionally small and pluggable. It is ephemeral and designed
    for single-process visibility. Later you can provide a DB or Redis-backed
    implementation with the same interface.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._records: Dict[str, CrawlRecord] = {}

    def start(self, config_name: str, config_id: Optional[int] = None) -> str:
        with self._lock:
            cid = str(uuid.uuid4())
            now = datetime.utcnow()
            rec = CrawlRecord(
                id=cid,
                config_name=config_name,
                config_id=config_id,
                status="running",
                started_at=now,
                last_seen=now,
            )
            self._records[cid] = rec
            return cid

    def update(self, crawl_id: str, *, pages_fetched: Optional[int] = None, links_found: Optional[int] = None, current_url: Optional[str] = None):
        with self._lock:
            rec = self._records.get(crawl_id)
            if not rec:
                return False
            if pages_fetched is not None:
                rec.pages_fetched = pages_fetched
            if links_found is not None:
                rec.links_found = links_found
            if current_url is not None:
                rec.current_url = current_url
            rec.last_seen = datetime.utcnow()
            return True

    def finish(self, crawl_id: str, *, status: str = "finished", error: Optional[str] = None):
        with self._lock:
            rec = self._records.get(crawl_id)
            if not rec:
                return False
            rec.status = status
            rec.finished_at = datetime.utcnow()
            rec.last_seen = rec.finished_at
            if error:
                rec.error = error
            return True

    def get(self, crawl_id: str) -> Optional[Dict]:
        with self._lock:
            rec = self._records.get(crawl_id)
            return asdict(rec) if rec else None

    def list_active(self) -> List[Dict]:
        with self._lock:
            return [asdict(r) for r in self._records.values() if r.status == "running"]
