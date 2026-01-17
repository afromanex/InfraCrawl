-- Migration: Add discovered_depth column to track at what depth a page was discovered
-- Used for iterative depth-based crawling to support proper resume functionality

ALTER TABLE pages ADD COLUMN discovered_depth INTEGER DEFAULT NULL;

-- Index to quickly find pages at a specific depth that still need fetching
CREATE INDEX idx_pages_discovered_depth ON pages(config_id, discovered_depth, page_content) 
WHERE page_content IS NULL;
