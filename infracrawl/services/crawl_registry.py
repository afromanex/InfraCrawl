from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import deque
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


@dataclass(frozen=True)
class CrawlHandle:
    crawl_id: str
    stop_event: threading.Event


class _InMemoryCrawlRecordStore:
    def __init__(self, *, max_completed_records: int):
        if max_completed_records < 0:
            raise ValueError("max_completed_records must be >= 0")
        self._records: Dict[str, CrawlRecord] = {}
        self._max_completed_records = max_completed_records
        self._completed_order = deque()
        self._completed_set = set()

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
        if self._max_completed_records == 0:
            # Caller will evict immediately.
            self._completed_order.append(crawl_id)
            return
        if crawl_id in self._completed_set:
            return
        self._completed_set.add(crawl_id)
        self._completed_order.append(crawl_id)

    def _evict_completed_overflow(self) -> List[str]:
        evicted: List[str] = []
        while len(self._completed_order) > self._max_completed_records:
            oldest = self._completed_order.popleft()
            self._completed_set.discard(oldest)
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


class _InMemoryCrawlCancellationManager:
    def __init__(self, *, event_factory=threading.Event):
        self._event_factory = event_factory
        self._cancel_events: Dict[str, threading.Event] = {}

    def create(self, crawl_id: str) -> threading.Event:
        ev = self._event_factory()
        self._cancel_events[crawl_id] = ev
        return ev

    def get(self, crawl_id: str) -> Optional[threading.Event]:
        return self._cancel_events.get(crawl_id)

    def request_cancel(self, crawl_id: str) -> bool:
        ev = self._cancel_events.get(crawl_id)
        if not ev:
            return False
        ev.set()
        return True

    def cleanup(self, crawl_id: str) -> None:
        ev = self._cancel_events.pop(crawl_id, None)
        if ev:
            ev.set()


class InMemoryCrawlRegistry:
    """Thread-safe in-memory registry for active and recent crawls.

    This is intentionally small and pluggable. It is ephemeral and designed
    for single-process visibility. Later you can provide a DB or Redis-backed
    implementation with the same interface.
    """

    def __init__(self, *, max_completed_records: int = 1000):
        self._lock = threading.Lock()
        self._records = _InMemoryCrawlRecordStore(max_completed_records=max_completed_records)
        self._cancellation = _InMemoryCrawlCancellationManager()

    def start(self, config_name: str, config_id: Optional[int] = None) -> CrawlHandle:
        with self._lock:
            cid = str(uuid.uuid4())
            now = datetime.utcnow()
            self._records.create_running(
                crawl_id=cid,
                config_name=config_name,
                config_id=config_id,
                now=now,
            )
            stop_event = self._cancellation.create(cid)
            return CrawlHandle(crawl_id=cid, stop_event=stop_event)

    def update(self, crawl_id: str, *, pages_fetched: Optional[int] = None, links_found: Optional[int] = None, current_url: Optional[str] = None):
        with self._lock:
            return self._records.update(
                crawl_id,
                pages_fetched=pages_fetched,
                links_found=links_found,
                current_url=current_url,
                now=datetime.utcnow(),
            )

    def finish(self, crawl_id: str, *, status: str = "finished", error: Optional[str] = None):
        with self._lock:
            now = datetime.utcnow()
            ok = self._records.finish(crawl_id, status=status, error=error, now=now)
            if ok:
                self._cancellation.cleanup(crawl_id)
                for evicted_id in self._records.evict_completed_overflow():
                    self._cancellation.cleanup(evicted_id)
            return ok

    def get(self, crawl_id: str) -> Optional[Dict]:
        with self._lock:
            rec = self._records.get(crawl_id)
            return asdict(rec) if rec else None

    def get_stop_event(self, crawl_id: str) -> Optional[threading.Event]:
        with self._lock:
            return self._cancellation.get(crawl_id)

    def cancel(self, crawl_id: str) -> bool:
        """Request cancellation for a running crawl. This sets the cancel event
        and marks the crawl as cancelled (finish time set).
        """
        with self._lock:
            now = datetime.utcnow()
            # Set the stop signal first so anyone holding the event observes it.
            if not self._cancellation.request_cancel(crawl_id):
                return False

            # Mark cancelled in records.
            if not self._records.mark_cancelled(crawl_id, now=now):
                return False

            # Immediately drop the stop-event mapping to prevent leaks if the crawl
            # never calls finish(). Callers that already hold the event still have it.
            self._cancellation.cleanup(crawl_id)

            for evicted_id in self._records.evict_completed_overflow():
                self._cancellation.cleanup(evicted_id)

            return True

    def list_active(self) -> List[Dict]:
        with self._lock:
            return [asdict(r) for r in self._records.list_active()]
