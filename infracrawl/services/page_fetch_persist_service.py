import logging
from datetime import datetime, timezone
from typing import Optional

from infracrawl.services.http_service import HttpService
from infracrawl.services.html_text_extractor import HtmlTextExtractor, TextExtractor
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.crawl_session import CrawlSession
from infracrawl.domain.page import Page as DomainPage
import hashlib

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

    def _get_config_id(self, url: str, context: Optional[CrawlSession]) -> Optional[int]:
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

    def fetch_and_persist(self, url: str, context: Optional[CrawlSession] = None) -> Optional[DomainPage]:
        """Fetch `url` and persist it, returning the domain `Page`.

        If the Content-Type is not supported (non-text/HTML), log and skip persistence.
        """
        response = self.http_service.fetch(url)

        ct = (getattr(response, 'content_type', None) or '').lower()
        # Supported: text/html, application/xhtml+xml, any text/*
        is_supported = (ct.startswith('text/') or 'text/html' in ct or 'application/xhtml+xml' in ct or ct == '')
        if not is_supported:
            logger.info("Content type not supported %s. Skipping %s", ct or 'unknown', url)
            return None

        fetched_at = datetime.now(timezone.utc)
        config_id = self._get_config_id(url, context)
        plain, filtered = self.text_extractor.extract(response.text)
        base_for_hash = filtered or plain or (response.text or "")
        content_hash = hashlib.sha256(base_for_hash.encode("utf-8")).hexdigest() if base_for_hash is not None else None

        page_obj = DomainPage(
            page_id=None,  # Will be assigned by DB
            page_url=url,
            page_content=response.text,
            plain_text=plain,
            filtered_plain_text=filtered,
            http_status=self._coerce_http_status(getattr(response, 'status_code', None) or getattr(response, 'status', None)),
            fetched_at=self._coerce_fetched_at(fetched_at),
            config_id=config_id,
            content_hash=content_hash,
        )
        page = self.pages_repo.upsert_page(page_obj)
        return page

    def extract_and_persist(
        self,
        page: DomainPage,
    ) -> bool:
        """Extract text from page content, persist it, and mutate page in-place.
        
        Mutates: page.plain_text, page.filtered_plain_text, page.content_hash, page.page_id, page.fetched_at
        Returns: True on success, False on failure
        """
        if page.page_content is None:
            logger.warning("Cannot extract from page with no content: %s", page.page_url)
            return False
            
        config_id = page.config_id or self._get_config_id(page.page_url, None)
        plain, filtered = self.text_extractor.extract(page.page_content)
        base_for_hash = filtered or plain or (page.page_content or "")
        content_hash = hashlib.sha256(base_for_hash.encode("utf-8")).hexdigest() if base_for_hash is not None else None

        # Mutate page with extracted data
        page.plain_text = plain
        page.filtered_plain_text = filtered
        page.content_hash = content_hash
        page.config_id = config_id
        if page.fetched_at is None:
            page.fetched_at = datetime.now(timezone.utc)
        
        # Persist and get page_id
        try:
            persisted_page = self.pages_repo.upsert_page(page)
            page.page_id = persisted_page.page_id
            return True
        except Exception as e:
            logger.error("Failed to persist page %s: %s", page.page_url, e, exc_info=True)
            return False
