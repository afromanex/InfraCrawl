-- Migration: add plain_text column to pages
ALTER TABLE pages ADD COLUMN IF NOT EXISTS plain_text TEXT;
CREATE INDEX IF NOT EXISTS idx_pages_plain_text ON pages USING gin (to_tsvector('english', COALESCE(plain_text, '')));
