import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  LoginResponse,
  User,
  CrawlerConfig,
  CrawlRun,
  CrawlStats,
} from '../models';

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
    return this.http.get<CrawlerConfig[]>(`${this.baseUrl}/crawlers/configs`);
  }

  getConfig(configId: number): Observable<CrawlerConfig> {
    return this.http.get<CrawlerConfig>(
      `${this.baseUrl}/crawlers/configs/${configId}`
    );
  }

  // Jobs
  getActiveJobs(): Observable<CrawlRun[]> {
    return this.http.get<CrawlRun[]>(`${this.baseUrl}/crawlers/active`);
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
  stopCrawl(configId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/crawlers/${configId}/stop`, {});
  }

  resumeCrawl(configId: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/crawlers/${configId}/resume`, {});
  }

  deleteCrawlData(configId: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}/crawlers/${configId}/data`);
  }

  // Stats
  getJobStats(configId: number): Observable<CrawlStats> {
    return this.http.get<CrawlStats>(
      `${this.baseUrl}/crawlers/stats/${configId}`
    );
  }
}
