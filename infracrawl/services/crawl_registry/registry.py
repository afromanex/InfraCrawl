from __future__ import annotations

import threading
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional

from .cancellation import _InMemoryCrawlCancellationManager
from .models import CrawlHandle, CrawlRecord
from .store import _InMemoryCrawlRecordStore


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
