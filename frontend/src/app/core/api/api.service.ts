import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LoginResponse, User, CrawlerConfig, CrawlRun } from '../models';

@Injectable({
  providedIn: 'root',
})
export class APIService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  // Auth
  login(password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.baseUrl}/auth/login`, {
      password,
    });
  }

  getCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/auth/me`);
  }

  // Configs
  getConfigs(): Observable<CrawlerConfig[]> {
    return this.http.get<CrawlerConfig[]>(`${this.baseUrl}/configs/`);
  }

  getConfig(configPath: string): Observable<string> {
    return this.http.get(`${this.baseUrl}/configs/${encodeURIComponent(configPath)}`,
      { responseType: 'text' });
  }

  // Jobs
  getActiveJobs(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/crawlers/active`);
  }

  getJobRuns(
    configId?: number,
    limit: number = 20,
    offset: number = 0
  ): Observable<CrawlRun[]> {
    let url = `${this.baseUrl}/crawlers/runs?limit=${limit}&offset=${offset}`;
    if (configId) {
      url += `&config_id=${configId}`;
    }
    return this.http.get<CrawlRun[]>(url);
  }

  getJobDetail(runId: number): Observable<CrawlRun> {
    return this.http.get<CrawlRun>(`${this.baseUrl}/crawlers/runs/${runId}`);
  }

  // Job Controls
  startCrawl(configPath: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/crawlers/crawl/${encodeURIComponent(configPath)}/start`, {});
  }

  stopCrawl(configId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/crawlers/${configId}/stop`, {});
  }

  cancelCrawl(crawlId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/crawlers/cancel/${crawlId}`, {});
  }

  resumeCrawl(configId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/crawlers/${configId}/resume`, {});
  }

  deleteCrawlData(configId: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/crawlers/${configId}/data`);
  }

  removeConfigData(configPath: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/crawlers/remove?config=${encodeURIComponent(configPath)}`);
  }

  // Stats
  getJobStats(configPath: string): Observable<{ config_path: string; pages: number; links: number }> {
    return this.http.get<{ config_path: string; pages: number; links: number }>(
      `${this.baseUrl}/crawlers/stats/${encodeURIComponent(configPath)}`
    );
  }
}
