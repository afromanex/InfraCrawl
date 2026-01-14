import logging
from datetime import datetime
from typing import Optional

from infracrawl.services.http_service import HttpService
from infracrawl.repository.pages import PagesRepository
from infracrawl.domain.crawl_context import CrawlContext
from infracrawl.domain.page import Page as DomainPage
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# TODO: SRP - PageFetchPersistService does 3 jobs: (1) HTTP fetch via HttpService (2) HTML text extraction (plain + filtered) (3) DB persistence via PagesRepository. Concrete risk: changing HTML filtering (e.g., ML-based) requires editing service with fetch/persist logic. Minimal fix: extract TextExtractor class with extract_texts(html) method; inject in __init__.
# TODO: DIP - _extract_text_from_body hardcodes BeautifulSoup(body, "html.parser"). Concrete risk: tests need full HTML parsing; cannot swap to fast lxml. Minimal fix: accept html_parser callable in __init__ (default=BeautifulSoup); call self.html_parser(body, "html.parser").
class PageFetchPersistService:
    """Service that fetches a page via `HttpService` and persists it using `PagesRepository`.

    It returns the domain `Page` object populated from the repository so callers
    can operate on the domain model directly.
    """

    def __init__(self, http_service: HttpService, pages_repo: PagesRepository):
        self.http_service = http_service
        self.pages_repo = pages_repo

    def _extract_texts_from_soup(self, soup: BeautifulSoup) -> tuple[str, str]:
        """Extract both plain and filtered text from parsed HTML soup.
        
        Returns: (plain_text, filtered_plain_text)
        """
        # Generate unfiltered plain text
        plain = soup.get_text(separator=" ", strip=True)
        
        # Generate filtered plain text by removing boilerplate
        filtered = self._extract_content_text_from_soup(soup)
        
        return plain, filtered

    def _extract_content_text_from_soup(self, soup: BeautifulSoup) -> str:
        """Extract main content text from BeautifulSoup object, removing navigation, headers, footers, etc.
        
        This method removes common non-content elements before extracting text:
        - Navigation elements (nav, menu)
        - Headers and footers
        - Scripts and styles
        - Forms and buttons
        - Sidebars and ads
        - Other boilerplate content
        """
        # TODO: Over-engineered filtering with soup cloning, double loops, lambda class matchers. Most sites don't need this. Simplify to just remove script/style/nav tags, skip the pattern matching loops and cloning.
        # Clone soup to avoid mutating original
        soup = BeautifulSoup(str(soup), "html.parser")
        
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

    def _extract_text_from_body(self, body: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Extract plain and filtered text from HTML body.
        
        Returns: (plain_text, filtered_plain_text) or (None, None) on error.
        """
        if not body:
            return None, None
        
        # TODO: Dependency Inversion violation - hardcoded BeautifulSoup parser ("html.parser"). Risk: cannot use lxml or html5lib without editing service; testing requires real HTML parsing. Refactor: inject IHtmlParser interface with parse(html) -> ParsedDocument; BeautifulSoup becomes implementation detail.
        # RESPONSE: Valid point. However, for simplicity we will keep it as is for now.
        try:
            soup = BeautifulSoup(body, "html.parser")
            return self._extract_texts_from_soup(soup)
        except Exception:
            logger.exception("Error extracting text from HTML body")
            return None, None

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
                logger.exception("Error getting config_id from context for %s", url)
                config_id = None

        plain, filtered = self._extract_text_from_body(body)

        page = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id, plain_text=plain, filtered_plain_text=filtered)
        return page

    # CLAUDE: status should be int not str - persist() signature is wrong, callers pass int
    def persist(self, url: str, status: int, body: Optional[str], fetched_at: str, context: Optional[CrawlContext] = None) -> DomainPage:
        """Persist a fetched page and return the domain `Page`."""
        config_id = None
        if context and getattr(context, 'config', None):
            try:
                config_id = context.config.config_id
            except Exception:
                logger.exception("Error getting config_id from context for %s", url)
                config_id = None

        plain, filtered = self._extract_text_from_body(body)

        page = self.pages_repo.upsert_page(url, body, status, fetched_at, config_id=config_id, plain_text=plain, filtered_plain_text=filtered)
        return page
