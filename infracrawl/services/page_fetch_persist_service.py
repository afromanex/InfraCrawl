import logging
from datetime import datetime, timezone
from typing import Optional

from infracrawl.services.http_service import HttpService
from infracrawl.services.html_text_extractor import HtmlTextExtractor, TextExtractor
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.page import Page as DomainPage

logger = logging.getLogger(__name__)
class PageFetchPersistService:
    """Service that fetches a page via `HttpService` and persists it using `PagesRepository`.

    It returns the domain `Page` object populated from the repository so callers
    can operate on the domain model directly.
    """

    def __init__(
        self,
        http_service: HttpService,
        pages_repo: PagesRepository,
        text_extractor: Optional[TextExtractor] = None,
    ):
        self.http_service = http_service
        self.pages_repo = pages_repo
        self.text_extractor = text_extractor or HtmlTextExtractor()

    def _get_config_id(self, url: str, context: Optional[CrawlContext]) -> Optional[int]:
        if context is None or getattr(context, 'config', None) is None:
            return None
        try:
            return context.config.config_id
        except Exception:
            logger.exception("Error getting config_id from context for %s", url)
            return None

    def _coerce_http_status(self, status: object) -> Optional[int]:
        if status is None:
            return None
        try:
            return int(status)
        except Exception:
            logger.exception("Invalid http status: %r", status)
            return None

    def _coerce_fetched_at(self, fetched_at: object) -> Optional[datetime]:
        if fetched_at is None:
            return None
        if isinstance(fetched_at, datetime):
            return fetched_at
        if isinstance(fetched_at, str):
            try:
                dt = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
                return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
            except Exception:
                logger.exception("Invalid fetched_at: %r", fetched_at)
                return None
        logger.exception("Invalid fetched_at type: %r", type(fetched_at))
        return None

    def fetch_and_persist(self, url: str, context: Optional[CrawlContext] = None) -> DomainPage:
        """Fetch `url` and persist it, returning the domain `Page`.

        Raises on storage errors.
        """
        response = self.http_service.fetch(url)

        fetched_at = datetime.now(timezone.utc)
        config_id = self._get_config_id(url, context)
        plain, filtered = self.text_extractor.extract(response.text)

        page_obj = DomainPage(
            page_id=None,  # Will be assigned by DB
            page_url=url,
            page_content=response.text,
            plain_text=plain,
            filtered_plain_text=filtered,
            http_status=self._coerce_http_status(getattr(response, 'status_code', None) or getattr(response, 'status', None)),
            fetched_at=self._coerce_fetched_at(fetched_at),
            config_id=config_id
        )
        page = self.pages_repo.upsert_page(page_obj)
        return page

    def extract_and_persist(
        self,
        url: str,
        status: int | str | None,
        body: Optional[str],
        fetched_at: datetime | str | None,
        context: Optional[CrawlContext] = None,
    ) -> DomainPage:
        """Extract text from fetched page body and persist it, returning the domain `Page`.
        
        Note: This method does NOT fetch the page - it expects the body to be provided.
        Use fetch_and_persist() if you need to fetch the page first.
        """
        config_id = self._get_config_id(url, context)
        plain, filtered = self.text_extractor.extract(body)

        page_obj = DomainPage(
            page_id=None,  # Will be assigned by DB
            page_url=url,
            page_content=body,
            plain_text=plain,
            filtered_plain_text=filtered,
            http_status=self._coerce_http_status(status),
            fetched_at=self._coerce_fetched_at(fetched_at),
            config_id=config_id
        )
        page = self.pages_repo.upsert_page(page_obj)
        return page
