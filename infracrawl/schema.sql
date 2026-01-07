CREATE TABLE IF NOT EXISTS pages (
  page_id SERIAL PRIMARY KEY,
  page_url TEXT UNIQUE NOT NULL,
  page_content TEXT,
  http_status INTEGER,
  fetched_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS links (
  link_id SERIAL PRIMARY KEY,
  link_from_id INTEGER NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
  link_to_id INTEGER NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
  anchor_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_pages_url ON pages (page_url);
CREATE INDEX IF NOT EXISTS idx_links_from ON links (link_from_id);
