import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError
from infracrawl import config


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


def upsert_page(page_url: str, page_content: str | None, http_status: int | None, fetched_at: str | None):
    """Insert or update a page row and return the page_id."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pages (page_url, page_content, http_status, fetched_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (page_url) DO UPDATE
                      SET page_content = EXCLUDED.page_content,
                          http_status = EXCLUDED.http_status,
                          fetched_at = EXCLUDED.fetched_at
                    RETURNING page_id
                    """,
                    (page_url, page_content, http_status, fetched_at),
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
