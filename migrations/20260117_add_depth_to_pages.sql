-- Track at what depth each page was discovered for iterative crawling
ALTER TABLE pages ADD COLUMN IF NOT EXISTS depth INTEGER DEFAULT NULL;

-- depth=0 for root URLs, depth=1 for pages discovered from root, etc.
-- NULL means depth not yet determined (shouldn't happen after refactor)
