-- Add content_hash to pages and an index for lookup
ALTER TABLE pages ADD COLUMN IF NOT EXISTS content_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_pages_content_hash ON pages(content_hash);
