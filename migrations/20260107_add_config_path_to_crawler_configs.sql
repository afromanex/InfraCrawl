-- Migration: Add config_path column to crawler_configs
ALTER TABLE crawler_configs ADD COLUMN config_path TEXT NOT NULL DEFAULT 'starkparks.yml';
