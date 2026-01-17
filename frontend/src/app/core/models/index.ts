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

export interface CrawlStats {
  run_id: number;
  config_id: number;
  config_path: string;
  pages_count: number;
  links_count: number;
  start_timestamp: string;
}
