from bs4 import BeautifulSoup
from urllib.parse import urljoin

# TODO: DIP - ContentReviewService hardcodes BeautifulSoup(html, "html.parser"). Concrete risk: tests require full HTML parsing; cannot use fast lxml parser without editing class. Minimal fix: accept parser_fn callable in __init__ (default=lambda h: BeautifulSoup(h, "html.parser")); tests pass lambda returning mock.
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
