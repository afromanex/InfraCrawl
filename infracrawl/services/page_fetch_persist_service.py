import logging
from datetime import datetime
from typing import Optional

from infracrawl.services.http_service import HttpService
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.page import Page as DomainPage
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PageFetchPersistService:
    """Service that fetches a page via `HttpService` and persists it using `PagesRepository`.

    It returns the domain `Page` object populated from the repository so callers
    can operate on the domain model directly.
    """

    def __init__(self, http_service: HttpService, pages_repo: PagesRepository):
        self.http_service = http_service
        self.pages_repo = pages_repo

    def fetch_and_persist(self, url: str, context: Optional[CrawlContext] = None) -> DomainPage:
        """Fetch `url` and persist it, returning the domain `Page`.

        Raises on storage errors.
        """
        status, body = self.http_service.fetch(url)

        fetched_at = datetime.utcnow().isoformat()
        config_id = None
        if context and getattr(context, 'config', None):
            try:
                config_id = context.config.config_id
            except Exception:
                config_id = None

        plain = None
        try:
            if body:
                soup = BeautifulSoup(body, "html.parser")
                plain = soup.get_text(separator="\n", strip=True)
        except Exception:
            plain = None

        page = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id, plain_text=plain)
        return page

    def persist(self, url: str, status: str, body: Optional[str], fetched_at: str, context: Optional[CrawlContext] = None) -> DomainPage:
        """Persist a fetched page and return the domain `Page`."""
        config_id = None
        if context and getattr(context, 'config', None):
            try:
                config_id = context.config.config_id
            except Exception:
                config_id = None

        plain = None
        try:
            if body:
                soup = BeautifulSoup(body, "html.parser")
                plain = soup.get_text(separator="\n", strip=True)
        except Exception:
            plain = None

        page = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id, plain_text=plain)
        return page
