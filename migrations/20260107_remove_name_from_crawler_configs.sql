-- Migration: Remove `name` column and enforce uniqueness on config_path
-- Ensure `config_path` exists and populate it from `name` if necessary, then drop `name`.
ALTER TABLE crawler_configs ADD COLUMN IF NOT EXISTS config_path TEXT;
UPDATE crawler_configs SET config_path = name WHERE config_path IS NULL AND name IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_crawler_configs_config_path ON crawler_configs (config_path);
ALTER TABLE crawler_configs ALTER COLUMN config_path SET NOT NULL;
ALTER TABLE crawler_configs DROP COLUMN IF EXISTS name;
