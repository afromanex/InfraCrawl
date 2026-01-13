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

    def _extract_content_text(self, html: str) -> str:
        """Extract main content text from HTML, removing navigation, headers, footers, etc.
        
        This method removes common non-content elements before extracting text:
        - Navigation elements (nav, menu)
        - Headers and footers
        - Scripts and styles
        - Forms and buttons
        - Sidebars and ads
        - Other boilerplate content
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove unwanted elements that don't contain main content
        unwanted_tags = [
            'script', 'style', 'noscript',  # Code and styling
            'nav', 'header', 'footer',      # Navigation and structural elements
            'aside', 'sidebar',              # Sidebars
            'form', 'button',                # Interactive elements
            'iframe', 'embed', 'object',     # Embedded content
            'select', 'input', 'textarea',   # Form inputs
            'svg', 'canvas',                 # Graphics
        ]
        
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements by common class/id names associated with navigation and boilerplate
        unwanted_patterns = [
            'nav', 'menu', 'sidebar', 'header', 'footer',
            'advertisement', 'ad', 'banner', 'popup',
            'breadcrumb', 'social', 'share', 'cookie',
            'related', 'recommend', 'promo', 'widget'
        ]
        
        for pattern in unwanted_patterns:
            # Remove by class
            for element in soup.find_all(class_=lambda x: x and pattern in x.lower()):
                element.decompose()
            # Remove by id
            for element in soup.find_all(id=lambda x: x and pattern in x.lower()):
                element.decompose()
        
        # Extract text from remaining content
        text = soup.get_text(separator="\n", strip=True)
        return text

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
        filtered = None
        try:
            if body:
                # Generate unfiltered plain text
                soup = BeautifulSoup(body, "html.parser")
                plain = soup.get_text(separator=" ", strip=True)
                # Generate filtered plain text
                filtered = self._extract_content_text(body)
        except Exception:
            plain = None
            filtered = None

        page = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id, plain_text=plain, filtered_plain_text=filtered)
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
        filtered = None
        try:
            if body:
                # Generate unfiltered plain text
                soup = BeautifulSoup(body, "html.parser")
                plain = soup.get_text(separator=" ", strip=True)
                # Generate filtered plain text
                filtered = self._extract_content_text(body)
        except Exception:
            plain = None
            filtered = None

        page = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id, plain_text=plain, filtered_plain_text=filtered)
        return page
