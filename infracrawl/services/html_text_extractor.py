import logging
from typing import Callable, Optional, Protocol

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TextExtractor(Protocol):
    def extract(self, body: Optional[str]) -> tuple[Optional[str], Optional[str]]: ...


class HtmlTextExtractor:
    def __init__(
        self,
        soup_factory: Optional[Callable[[str], BeautifulSoup]] = None,
    ):
        self._soup_factory = soup_factory or (lambda html: BeautifulSoup(html, "html.parser"))

    def extract(self, body: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not body:
            return None, None

        try:
            soup = self._soup_factory(body)
            plain = soup.get_text(separator=" ", strip=True)
            filtered = self._extract_content_text_from_soup(soup)
            return plain, filtered
        except Exception:
            logger.exception("Error extracting text from HTML body")
            return None, None

    def _extract_content_text_from_soup(self, soup: BeautifulSoup) -> str:
        # Clone soup to avoid mutating original
        soup = self._soup_factory(str(soup))

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
        return soup.get_text(separator="\n", strip=True)
