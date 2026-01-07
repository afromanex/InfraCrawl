-- Add `crawls` table to log crawl runs

CREATE TABLE IF NOT EXISTS crawls (
    run_id SERIAL PRIMARY KEY,
    config_id INTEGER NULL,
    start_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    end_timestamp TIMESTAMP WITH TIME ZONE NULL,
    exception TEXT NULL
);
