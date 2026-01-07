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

-- Table for crawler configurations loaded from YAML files
CREATE TABLE IF NOT EXISTS crawler_configs (
  config_id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  root_urls JSONB NOT NULL,
  max_depth INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crawler_configs_name ON crawler_configs (name);

-- Ensure pages table has config_id column for association
ALTER TABLE pages ADD COLUMN IF NOT EXISTS config_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_pages_config ON pages (config_id);
