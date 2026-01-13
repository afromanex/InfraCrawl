-- Add filtered_plain_text column to pages table
ALTER TABLE pages ADD COLUMN IF NOT EXISTS filtered_plain_text TEXT;
