from bs4 import BeautifulSoup
from urllib.parse import urljoin

# TODO: Dependency Inversion violation - hardcoded BeautifulSoup dependency. Risk: cannot swap to lxml or custom parser without editing this class; testing requires HTML parsing. Refactor: inject IHtmlParser interface; BeautifulSoup becomes adapter.
# RESPONSE: Beautiful soup could be injected, but for simplicity we will keep it as is for now.

class ContentReviewService:
    def extract_links(self, base_url: str, html: str):
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            abs_url = urljoin(base_url, href)
            urls.append((abs_url, a.get_text(strip=True)))
        return urls

    # Add more content analysis methods as needed
