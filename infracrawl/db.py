import os
import time
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import OperationalError
except Exception:
    psycopg2 = None
    RealDictCursor = None
    OperationalError = Exception
from infracrawl import config
import json

# Optional SQLAlchemy-backed repository adapter
USE_SQLALCHEMY = os.getenv("USE_SQLALCHEMY") == "1"
if USE_SQLALCHEMY:
    try:
        from infracrawl.db.engine import init_orm
        from infracrawl.repository import PagesRepository, LinksRepository, ConfigsRepository

        _pages_repo = PagesRepository()
        _links_repo = LinksRepository()
        _configs_repo = ConfigsRepository()
    except Exception:
        _pages_repo = None
        _links_repo = None
        _configs_repo = None


def get_conn():
    dsn = config.DATABASE_URL or os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(dsn)


def init_db(retries: int = 10, delay: float = 1.0):
    """Create schema if it doesn't exist using `schema.sql`.

    Will retry connecting to the database `retries` times with `delay` seconds
    between attempts to handle cases where Postgres is starting.
    """
    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()

    # If using SQLAlchemy, create tables via ORM
    if USE_SQLALCHEMY and _pages_repo is not None:
        engine = _pages_repo.engine
        init_orm(engine)
        return

    attempt = 0
    while True:
        try:
            conn = get_conn()
            break
        except OperationalError as e:
            attempt += 1
            if attempt > retries:
                raise
            time.sleep(delay)

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
    finally:
        conn.close()


def upsert_page(page_url: str, page_content: str | None, http_status: int | None, fetched_at: str | None, config_id: int | None = None):
    """Insert or update a page row and return the page_id. Associates page with `config_id` if provided."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pages (page_url, page_content, http_status, fetched_at, config_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (page_url) DO UPDATE
                      SET page_content = EXCLUDED.page_content,
                          http_status = EXCLUDED.http_status,
                          fetched_at = EXCLUDED.fetched_at,
                          config_id = COALESCE(EXCLUDED.config_id, pages.config_id)
                    RETURNING page_id
                    """,
                    (page_url, page_content, http_status, fetched_at, config_id),
                )
                row = cur.fetchone()
                return row[0]
    finally:
        conn.close()



def ensure_page(page_url: str):
    """Ensure a page row exists for the given URL, return page_id.

    If the page exists, returns its id. Otherwise inserts a row with NULL
    content (discovered but not fetched).
    """
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pages (page_url)
                    VALUES (%s)
                    ON CONFLICT (page_url) DO NOTHING
                    RETURNING page_id
                    """,
                    (page_url,),
                )
                row = cur.fetchone()
                if row:
                    return row[0]
                # fetch existing id
                cur.execute("SELECT page_id FROM pages WHERE page_url = %s", (page_url,))
                return cur.fetchone()[0]
    finally:
        conn.close()


def insert_link(link_from_id: int, link_to_id: int, anchor_text: str | None):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO links (link_from_id, link_to_id, anchor_text)
                    VALUES (%s, %s, %s)
                    """,
                    (link_from_id, link_to_id, anchor_text),
                )
    finally:
        conn.close()


def upsert_config(name: str, root_urls: list, max_depth: int, robots: bool = True, refresh_days: int | None = None):
    """Insert or update a crawler configuration."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO crawler_configs (name, root_urls, max_depth, robots, refresh_days, updated_at)
                    VALUES (%s, %s::jsonb, %s, %s, %s, now())
                    ON CONFLICT (name) DO UPDATE
                      SET root_urls = EXCLUDED.root_urls,
                          max_depth = EXCLUDED.max_depth,
                          robots = EXCLUDED.robots,
                          refresh_days = EXCLUDED.refresh_days,
                          updated_at = now()
                    RETURNING config_id
                    """,
                    (name, json.dumps(root_urls), max_depth, robots, refresh_days),
                )
                row = cur.fetchone()
                return row[0]
    finally:
        conn.close()


def get_page_by_url(page_url: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT page_id, page_url, fetched_at FROM pages WHERE page_url = %s", (page_url,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    finally:
        conn.close()


def get_config(name: str):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT config_id, name, root_urls, max_depth, robots, refresh_days FROM crawler_configs WHERE name = %s", (name,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    finally:
        conn.close()


def get_config_by_id(config_id: int):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT config_id, name, root_urls, max_depth, robots, refresh_days FROM crawler_configs WHERE config_id = %s", (config_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    finally:
        conn.close()


def list_configs():
    if USE_SQLALCHEMY and _configs_repo is not None:
        return _configs_repo.list_configs()
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT config_id, name, root_urls, max_depth, robots, refresh_days, created_at, updated_at FROM crawler_configs")
                rows = cur.fetchall()
                from infracrawl.domain import CrawlerConfig
                return [CrawlerConfig(
                    config_id=r[0],
                    name=r[1],
                    root_urls=r[2],
                    max_depth=r[3],
                    robots=r[4],
                    refresh_days=r[5],
                    created_at=r[6],
                    updated_at=r[7]
                ) for r in rows]
    finally:
        conn.close()
    finally:
        conn.close()


def delete_config(name: str):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM crawler_configs WHERE name = %s", (name,))
    finally:
        conn.close()


def fetch_pages(full: bool = False, limit: int | None = None):
    if USE_SQLALCHEMY and _pages_repo is not None:
        return _pages_repo.fetch_pages(full=full, limit=limit)
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cols = ["page_id", "page_url", "http_status", "fetched_at"]
            if full:
                cols.append("page_content")
            sql = f"SELECT {', '.join(cols)} FROM pages ORDER BY page_id"
            if limit:
                sql += f" LIMIT {int(limit)}"
            cur.execute(sql)
            rows = cur.fetchall()
            from infracrawl.domain import Page
            out = []
            for r in rows:
                d = dict(r)
                fa = d.get("fetched_at")
                if fa is not None:
                    d["fetched_at"] = fa.isoformat()
                out.append(Page(
                    page_id=d["page_id"],
                    page_url=d["page_url"],
                    page_content=d.get("page_content"),
                    http_status=d.get("http_status"),
                    fetched_at=d.get("fetched_at"),
                    config_id=d.get("config_id")
                ))
            return out
    finally:
        conn.close()


def fetch_links(limit: int | None = None):
    if USE_SQLALCHEMY and _links_repo is not None:
        return _links_repo.fetch_links(limit=limit)
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT link_id, link_from_id, link_to_id, anchor_text FROM links ORDER BY link_id"
            if limit:
                sql += f" LIMIT {int(limit)}"
            cur.execute(sql)
            rows = cur.fetchall()
            from infracrawl.domain import Link
            return [Link(
                link_id=r["link_id"],
                link_from_id=r["link_from_id"],
                link_to_id=r["link_to_id"],
                anchor_text=r["anchor_text"]
            ) for r in rows]
    finally:
        conn.close()


# If requested, override the above functions with SQLAlchemy-backed implementations
if USE_SQLALCHEMY and _repo is not None:
    # simple delegations to the Repository methods
    def ensure_page(page_url: str):
        return _pages_repo.ensure_page(page_url)

    def get_page_by_url(page_url: str):
        return _pages_repo.get_page_by_url(page_url)

    def upsert_page(page_url: str, page_content: str | None, http_status: int | None, fetched_at: str | None, config_id: int | None = None):
        return _pages_repo.upsert_page(page_url, page_content, http_status, fetched_at, config_id=config_id)

    def insert_link(link_from_id: int, link_to_id: int, anchor_text: str | None):
        return _links_repo.insert_link(link_from_id, link_to_id, anchor_text)

    def upsert_config(name: str, root_urls: list, max_depth: int, robots: bool = True, refresh_days: int | None = None):
        return _configs_repo.upsert_config(name, root_urls, max_depth, robots=robots, refresh_days=refresh_days)

    def get_config(name: str):
        return _configs_repo.get_config(name)

    def get_config_by_id(config_id: int):
        return _configs_repo.get_config_by_id(config_id)

    def list_configs():
        return _configs_repo.list_configs()

    def delete_config(name: str):
        return _configs_repo.delete_config(name)

    def fetch_pages(full: bool = False, limit: int | None = None):
        return _pages_repo.fetch_pages(full=full, limit=limit)

    def fetch_links(limit: int | None = None):
        return _links_repo.fetch_links(limit=limit)
