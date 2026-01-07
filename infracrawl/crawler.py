from bs4 import BeautifulSoup
import requests
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime
from infracrawl import config
from infracrawl import db


class Crawler:
    def __init__(self, delay=None, user_agent=None):
        self.delay = delay if delay is not None else config.CRAWL_DELAY
        self.user_agent = user_agent or config.USER_AGENT

    def fetch(self, url: str):
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.status_code, resp.text

    def extract_links(self, base_url: str, html: str):
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            abs_url = urljoin(base_url, href)
            urls.append((abs_url, a.get_text(strip=True)))
        return urls

    def _same_host(self, base: str, other: str) -> bool:
        try:
            b = urlparse(base).hostname
            o = urlparse(other).hostname
            return b == o or (b and o and o.endswith('.' + b))
        except Exception:
            return False

    def crawl(self, start_url: str, max_depth: int | None = None):
        """Depth-limited recursive crawl starting at `start_url`.

        Stores pages and links in the database. Pages discovered but not yet
        fetched are created with NULL content.
        """
        max_depth = max_depth if max_depth is not None else config.DEFAULT_DEPTH
        visited = set()

        def _crawl_from(url: str, depth: int):
            if url in visited:
                return
            visited.add(url)

            # ensure page row exists
            from_id = db.ensure_page(url)

            if depth < 0:
                return

            try:
                status, body = self.fetch(url)
                fetched_at = datetime.utcnow().isoformat()
                page_id = db.upsert_page(url, body, status, fetched_at)
                print(f"Fetched {url} -> status {status}, page_id={page_id}")
            except Exception as e:
                print(f"Failed to fetch {url}: {e}")
                return

            time.sleep(self.delay)

            links = self.extract_links(url, body)
            for link_url, anchor in links:
                if not self._same_host(start_url, link_url):
                    continue
                to_id = db.ensure_page(link_url)
                db.insert_link(from_id, to_id, anchor)
                if depth - 1 >= 0:
                    _crawl_from(link_url, depth - 1)

        _crawl_from(start_url, max_depth)
