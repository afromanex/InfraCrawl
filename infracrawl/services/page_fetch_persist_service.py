import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from infracrawl.services.http_service import HttpService
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.crawl_context import CrawlContext

logger = logging.getLogger(__name__)


@dataclass
class PageFetchResult:
    url: str
    status: str
    body: Optional[str]
    page_id: Optional[int]
    fetched_at: str


class PageFetchPersistService:
    """Service that fetches a page via `HttpService` and persists it using `PagesRepository`.

    This extracts the fetch-and-persist responsibility out of `Crawler` so it can be
    tested and extended independently (retry policies, different persistence, etc.).
    """

    def __init__(self, http_service: HttpService, pages_repo: PagesRepository):
        self.http_service = http_service
        self.pages_repo = pages_repo

    def fetch_and_persist(self, url: str, context: Optional[CrawlContext] = None) -> PageFetchResult:
        """Fetch `url` and persist it. Raises on storage errors."""
        status, body = self.http_service.fetch(url)

        fetched_at = datetime.utcnow().isoformat()
        page_id = None
        config_id = None
        if context and getattr(context, 'config', None):
            try:
                config_id = context.config.config_id
            except Exception:
                config_id = None

        page_id = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id)

        return PageFetchResult(url=url, status=status, body=body, page_id=page_id, fetched_at=fetched_at)

    def persist(self, url: str, status: str, body: Optional[str], fetched_at: str, context: Optional[CrawlContext] = None) -> int:
        """Persist a fetched page. Raises on storage errors."""
        config_id = None
        if context and getattr(context, 'config', None):
            try:
                config_id = context.config.config_id
            except Exception:
                config_id = None

        page_id = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id)
        return page_id
