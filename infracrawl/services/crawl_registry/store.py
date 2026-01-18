from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

from .models import CrawlRecord


class CrawlRecordStore:
    def __init__(self, *, max_completed_records: int):
        if max_completed_records < 0:
            raise ValueError("max_completed_records must be >= 0")
        self._records: Dict[str, CrawlRecord] = {}
        self._max_completed_records = max_completed_records
        self._completed_order = deque()

    def create_running(self, *, crawl_id: str, config_name: str, config_id: Optional[int], now: datetime) -> CrawlRecord:
        rec = CrawlRecord(
            id=crawl_id,
            config_name=config_name,
            config_id=config_id,
            status="running",
            started_at=now,
            last_seen=now,
        )
        self._records[crawl_id] = rec
        return rec

    def _mark_completed_for_retention(self, crawl_id: str) -> None:
        self._completed_order.append(crawl_id)

    def _evict_completed_overflow(self) -> List[str]:
        evicted: List[str] = []
        while len(self._completed_order) > self._max_completed_records:
            oldest = self._completed_order.popleft()
            if oldest in self._records:
                del self._records[oldest]
                evicted.append(oldest)
        return evicted

    def get(self, crawl_id: str) -> Optional[CrawlRecord]:
        return self._records.get(crawl_id)

    def update(
        self,
        crawl_id: str,
        *,
        pages_fetched: Optional[int] = None,
        links_found: Optional[int] = None,
        current_url: Optional[str] = None,
        now: datetime,
    ) -> bool:
        rec = self._records.get(crawl_id)
        if not rec:
            return False

        if pages_fetched is not None:
            rec.pages_fetched = pages_fetched
        if links_found is not None:
            rec.links_found = links_found
        if current_url is not None:
            rec.current_url = current_url
            # Add to recent URLs history
            if current_url and current_url not in rec.recent_urls:
                rec.recent_urls.append(current_url)

        rec.last_seen = now
        return True

    def finish(self, crawl_id: str, *, status: str, error: Optional[str], now: datetime) -> bool:
        rec = self._records.get(crawl_id)
        if not rec:
            return False
        rec.status = status
        rec.finished_at = now
        rec.last_seen = now
        if error:
            rec.error = error
        self._mark_completed_for_retention(crawl_id)
        return True

    def mark_cancelled(self, crawl_id: str, *, now: datetime) -> bool:
        rec = self._records.get(crawl_id)
        if not rec:
            return False
        rec.status = "cancelled"
        rec.finished_at = now
        rec.last_seen = now
        self._mark_completed_for_retention(crawl_id)
        return True

    def evict_completed_overflow(self) -> List[str]:
        return self._evict_completed_overflow()

    def list_active(self) -> List[CrawlRecord]:
        return [r for r in self._records.values() if r.status == "running"]
