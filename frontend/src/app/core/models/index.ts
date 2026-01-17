export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  expires_in: number;
}

export interface User {
  user_id: string;
  email: string;
  role: string;
  permissions: string[];
}

export interface CrawlerConfig {
  config_id: number;
  config_path: string;
  root_urls: string[];
  max_depth: number;
  schedule: string | null;
  resume_on_application_restart: boolean;
  fetch_mode: string;
  robots: boolean;
  refresh_days: number | null;
}

export interface CrawlRun {
  run_id: number;
  config_id: number;
  config_path: string;
  start_timestamp: string;
  end_timestamp: string | null;
  exception: string | null;
  status: 'running' | 'completed' | 'failed' | 'stopped';
  pages_crawled?: number;
  current_depth?: number;
}

export interface ActiveCrawlRecord {
  id: string;
  config_name: string;
  config_id: number | null;
  status: string;
  started_at: string;
  last_seen: string;
  finished_at: string | null;
  pages_fetched: number;
  links_found: number;
  current_url: string | null;
  error: string | null;
}

export interface CrawlStats {
  run_id: number;
  config_id: number;
  config_path: string;
  pages_count: number;
  links_count: number;
  start_timestamp: string;
}
