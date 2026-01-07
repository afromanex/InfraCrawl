from bs4 import BeautifulSoup
import requests
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from infracrawl import config
from infracrawl import db
from urllib.parse import urlunparse
import requests
from urllib.parse import urljoin
from urllib.parse import urlparse as _urlparse
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from urllib.parse import SplitResult
from urllib.parse import urlsplit as _urlsplit
import urllib
from urllib.robotparser import RobotFileParser


class Crawler:
    def __init__(self, delay=None, user_agent=None):
        self.delay = delay if delay is not None else config.CRAWL_DELAY
        self.user_agent = user_agent or config.USER_AGENT
        self._rp_cache: dict[str, RobotFileParser] = {}

    def fetch(self, url: str):
        headers = {"User-Agent": self.user_agent}
        resp = requests.get(url, headers=headers, timeout=10)
        return resp.status_code, resp.text

    def _allowed_by_robots(self, url: str, robots_enabled: bool) -> bool:
        if not robots_enabled:
            return True
        try:
            parsed = _urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            if base in self._rp_cache:
                rp = self._rp_cache[base]
            else:
                rp = RobotFileParser()
                robots_url = urljoin(base, "/robots.txt")
                try:
                    r = requests.get(robots_url, headers={"User-Agent": self.user_agent}, timeout=5)
                    if r.status_code == 200:
                        lines = r.text.splitlines()
                        rp.parse(lines)
                    else:
                        # missing or inaccessible robots -> allow
                        rp = None
                except Exception:
                    rp = None
                self._rp_cache[base] = rp

            if rp is None:
                return True
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return True

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

    def crawl(self, start_url: str, max_depth: int | None = None, config_id: int | None = None):
        """Depth-limited recursive crawl starting at `start_url`.

        Stores pages and links in the database. Pages discovered but not yet
        fetched are created with NULL content.
        """
        max_depth = max_depth if max_depth is not None else config.DEFAULT_DEPTH
        visited = set()

        def _crawl_from(url: str, depth: int):
            if url in visited:
                print(f"Skipping (visited) {url}")
                return
            visited.add(url)

            # ensure page row exists
            from_id = db.ensure_page(url)

            # if ensure_page created without config_id, we'll set config_id when upserting after fetch

            if depth < 0:
                print(f"Skipping (max depth reached) {url} at depth {depth}")
                return

            # Check robots and refresh_days
            cfg_robots = True
            cfg_refresh_days = None
            if config_id is not None:
                cfg = db.get_config_by_id(config_id) if hasattr(db, 'get_config_by_id') else None
                if isinstance(cfg, dict):
                    cfg_robots = cfg.get('robots', True)
                    cfg_refresh_days = cfg.get('refresh_days')

            if not self._allowed_by_robots(url, cfg_robots):
                print(f"Skipping (robots) {url}")
                return

            # Check refresh_days: skip fetching if recently fetched
            if cfg_refresh_days is not None:
                page = db.get_page_by_url(url)
                if page and page.get('fetched_at'):
                    try:
                        last = page.get('fetched_at')
                        if isinstance(last, str):
                            try:
                                last_dt = datetime.fromisoformat(last)
                            except Exception:
                                last_dt = None
                        else:
                            last_dt = last
                        if last_dt is not None:
                            try:
                                # Normalize last_dt to UTC naive datetime for safe subtraction
                                if last_dt.tzinfo is not None:
                                    last_dt_utc = last_dt.astimezone(timezone.utc).replace(tzinfo=None)
                                else:
                                    last_dt_utc = last_dt
                                delta_days = (datetime.utcnow() - last_dt_utc).days
                                if delta_days < int(cfg_refresh_days):
                                    print(f"Skipping {url}; fetched {delta_days} days ago (< {cfg_refresh_days})")
                                    return
                            except Exception:
                                # If any error occurs comparing datetimes, fall through and fetch
                                pass
                    except Exception:
                        pass

            try:
                status, body = self.fetch(url)
                fetched_at = datetime.utcnow().isoformat()
                page_id = db.upsert_page(url, body, status, fetched_at, config_id=config_id)
                print(f"Fetched {url} -> status {status}, page_id={page_id}")
            except Exception as e:
                print(f"Failed to fetch {url}: {e}")
                return

            time.sleep(self.delay)

            links = self.extract_links(url, body)
            for link_url, anchor in links:
                if not self._same_host(start_url, link_url):
                    print(f"Skipping (external) {link_url} -> not same host as {start_url}")
                    continue
                to_id = db.ensure_page(link_url)
                db.insert_link(from_id, to_id, anchor)
                if depth - 1 >= 0:
                    _crawl_from(link_url, depth - 1)

        _crawl_from(start_url, max_depth)
