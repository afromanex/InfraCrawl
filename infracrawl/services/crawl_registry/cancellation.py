from __future__ import annotations

import threading
from typing import Dict, Optional


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
