import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil, interval, fromEvent, EMPTY, startWith, map, switchMap } from 'rxjs';
import { APIService } from '../../core/api/api.service';
import { CrawlerConfig } from '../../core/models';

interface ActiveJob {
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

@Component({
  selector: 'app-jobs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Active Jobs</h1>

      <!-- Start New Job Card -->
      <div class="bg-white rounded-lg shadow p-6 mb-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Start New Crawl</h2>
        <div class="flex gap-4 items-end">
          <div class="flex-1">
            <label for="config-select" class="block text-sm font-medium text-gray-700 mb-2">
              Select Configuration
            </label>
            <select
              id="config-select"
              [(ngModel)]="selectedConfigPath"
              class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">-- Choose a configuration --</option>
              <option *ngFor="let cfg of configs" [value]="cfg.config_path">
                {{ cfg.config_path }}
              </option>
            </select>
          </div>
          <button
            type="button"
            (click)="startCrawl()"
            [disabled]="!selectedConfigPath || startingCrawl"
            class="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ startingCrawl ? 'Starting...' : 'Start Crawl' }}
          </button>
        </div>
      </div>

      <div *ngIf="loading" class="text-gray-600">Loading jobs...</div>

      <div *ngIf="error" class="rounded-md bg-red-50 p-3 text-sm text-red-800 mb-4">
        {{ error }}
      </div>

      <div *ngIf="!loading && jobs.length === 0" class="text-gray-600">
        No active jobs at the moment.
      </div>

      <div *ngIf="jobs.length > 0" class="overflow-hidden rounded-lg shadow ring-1 ring-black ring-opacity-5">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Config
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pages (Session)
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Links (Session)
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Started
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <ng-container *ngFor="let job of jobs">
              <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ job.config_name }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <span [ngClass]="getStatusClass(job.status)">
                    {{ job.status }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ job.pages_fetched }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ job.links_found }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatTime(job.started_at) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                  <span
                    role="button"
                    tabindex="0"
                    class="text-blue-600 hover:underline cursor-pointer"
                    (click)="toggleLog(job.id)"
                    (keydown.enter)="toggleLog(job.id)"
                    (keydown.space)="toggleLog(job.id)"
                  >
                    {{ showingLog === job.id ? 'Hide Log' : 'See Log' }}
                  </span>
                  <button
                    *ngIf="job.status === 'running'"
                    type="button"
                    class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1"
                    (click)="cancelJob(job.id)"
                  >
                    Cancel
                  </button>
                </td>
              </tr>
              <tr *ngIf="showingLog === job.id" class="bg-gray-50">
                <td colspan="6" class="px-6 py-4">
                  <div class="text-sm">
                    <div class="mb-2">
                      <strong class="text-gray-700">Recent Pages (Most Recent First):</strong>
                    </div>
                    <div *ngIf="loadingLog === job.id" class="text-gray-500">Loading...</div>
                    <div *ngIf="logError === job.id" class="text-red-600">Failed to load log</div>
                    <div *ngIf="!crawlLogs[job.id] || crawlLogs[job.id].length === 0" class="text-gray-500">
                      No pages crawled yet
                    </div>
                    <ul *ngIf="crawlLogs[job.id] && crawlLogs[job.id].length > 0" class="space-y-1 max-h-64 overflow-y-auto">
                      <li *ngFor="let url of crawlLogs[job.id]" class="text-xs break-all font-mono text-gray-700">
                        {{ url }}
                      </li>
                    </ul>
                  </div>
                </td>
              </tr>
              <tr *ngIf="job.error && expanded.has(job.id)">
                <td colspan="6" class="px-6 py-4 bg-red-50 text-sm text-red-700">
                  <strong>Error:</strong> {{ job.error }}
                </td>
              </tr>
              <tr *ngIf="expanded.has(job.id)" class="bg-gray-50">
                <td colspan="6" class="px-6 py-4 text-sm">
                  <div class="space-y-2">
                    <div><strong>Job ID:</strong> {{ job.id }}</div>
                    <div><strong>Last Updated:</strong> {{ formatTime(job.last_seen) }}</div>
                    <div *ngIf="job.finished_at"><strong>Finished:</strong> {{ formatTime(job.finished_at) }}</div>
                  </div>
                </td>
              </tr>
            </ng-container>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [],
})
export class JobsComponent implements OnInit, OnDestroy {
  jobs: ActiveJob[] = [];
  configs: CrawlerConfig[] = [];
  selectedConfigPath: string = '';
  startingCrawl = false;
  loading = false;
  error: string | null = null;
  expanded = new Set<string>();
  showingLog: string | null = null;
  loadingLog: string | null = null;
  logError: string | null = null;
  crawlLogs: { [crawlId: string]: string[] } = {};
  private destroy$ = new Subject<void>();
  private pollInterval = 2000; // Poll every 2 seconds
  private initialLoad = true;

  constructor(private api: APIService) {}

  ngOnInit(): void {
    this.fetchConfigs();
    this.fetchJobs();
    // Poll for job updates; pause when tab is hidden
    fromEvent(document, 'visibilitychange')
      .pipe(
        startWith(0),
        map(() => !document.hidden),
        switchMap((visible: boolean) => (visible ? interval(this.pollInterval) : EMPTY)),
        takeUntil(this.destroy$)
      )
      .subscribe(() => this.fetchJobs());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private fetchConfigs(): void {
    this.api
      .getConfigs()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (configs: CrawlerConfig[]) => {
          this.configs = configs;
        },
        error: (err: any) => {
          console.error('Failed to load configs:', err);
        },
      });
  }

  private fetchJobs(): void {
    if (this.initialLoad) {
      this.loading = true;
    }
    this.api
      .getActiveJobs()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: any) => {
          this.jobs = response.active || [];
          this.error = null;
          this.loading = false;
          this.initialLoad = false;
          // If a log is open, refresh it on each poll
          if (this.showingLog) {
            this.loadLog(this.showingLog);
          }
        },
        error: (err: any) => {
          this.error = err?.error?.detail || 'Failed to load active jobs';
          this.loading = false;
        },
      });
  }

  cancelJob(jobId: string): void {
    this.api
      .cancelCrawl(jobId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.fetchJobs();
        },
        error: (err: any) => {
          this.error = err?.error?.detail || 'Failed to cancel job';
        },
      });
  }
  toggleLog(jobId: string): void {
    if (this.showingLog === jobId) {
      this.showingLog = null;
    } else {
      this.showingLog = jobId;
      this.loadLog(jobId);
    }
  }

  refreshLog(jobId: string): void {
    this.loadLog(jobId);
  }

  private loadLog(jobId: string): void {
    const hasExisting = !!this.crawlLogs[jobId] && this.crawlLogs[jobId].length > 0;
    if (!hasExisting) {
      this.loadingLog = jobId;
    }
    this.logError = null;
    const job = this.jobs.find(j => j.id === jobId);
    const configPath = job?.config_name || '';
    this.api
      .getCrawlLogByConfig(configPath)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (response: { config: string; recent_urls: string[] }) => {
          this.crawlLogs[jobId] = (response.recent_urls || []).slice(0, 10);
          this.loadingLog = null;
        },
        error: (err: any) => {
          console.error('Failed to load crawl log:', err);
          // If the crawl is missing (404), show an empty log instead of error
          if (err && (err.status === 404 || err.statusCode === 404)) {
            this.crawlLogs[jobId] = [];
            this.logError = null;
          } else {
            this.logError = jobId;
          }
          this.loadingLog = null;
        },
      });
  }

  // Removed fallback helper to strictly show backend-provided recent URLs
  startCrawl(): void {
    if (!this.selectedConfigPath) {
      return;
    }

    this.startingCrawl = true;
    this.error = null;

    this.api
      .startCrawl(this.selectedConfigPath)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.startingCrawl = false;
          this.selectedConfigPath = '';
          // Give the job a moment to appear in the registry
          setTimeout(() => this.fetchJobs(), 500);
        },
        error: (err: any) => {
          this.startingCrawl = false;
          this.error = err?.error?.detail || 'Failed to start crawl';
        },
      });
  }

  getStatusClass(status: string): string {
    const baseClass = 'px-2 py-1 rounded-full text-xs font-semibold';
    switch (status) {
      case 'running':
        return baseClass + ' bg-blue-100 text-blue-800';
      case 'finished':
        return baseClass + ' bg-green-100 text-green-800';
      case 'cancelled':
        return baseClass + ' bg-yellow-100 text-yellow-800';
      case 'failed':
        return baseClass + ' bg-red-100 text-red-800';
      default:
        return baseClass + ' bg-gray-100 text-gray-800';
    }
  }

  formatTime(timestamp: string): string {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return date.toLocaleString();
  }
}
