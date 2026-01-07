-- Migration: Drop old config fields from crawler_configs
ALTER TABLE crawler_configs
    DROP COLUMN root_urls,
    DROP COLUMN max_depth,
    DROP COLUMN robots,
    DROP COLUMN refresh_days;
