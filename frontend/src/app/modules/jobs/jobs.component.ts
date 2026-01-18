import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, takeUntil, interval } from 'rxjs';
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
                Current URL
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
                <td class="px-6 py-4 text-sm text-gray-600 truncate max-w-xs" [title]="job.current_url || ''">
                  {{ job.current_url ? (job.current_url | slice:0:50) + '...' : '—' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <button
                    *ngIf="job.status === 'running'"
                    type="button"
                    class="text-red-600 hover:text-red-800"
                    (click)="cancelJob(job.id)"
                  >
                    Cancel
                  </button>
                  <span *ngIf="job.status !== 'running'" class="text-gray-400">—</span>
                </td>
              </tr>
              <tr *ngIf="job.error && expanded.has(job.id)">
                <td colspan="7" class="px-6 py-4 bg-red-50 text-sm text-red-700">
                  <strong>Error:</strong> {{ job.error }}
                </td>
              </tr>
              <tr *ngIf="expanded.has(job.id)" class="bg-gray-50">
                <td colspan="7" class="px-6 py-4 text-sm">
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
  private destroy$ = new Subject<void>();
  private pollInterval = 5000; // Poll every 5 seconds

  constructor(private api: APIService) {}

  ngOnInit(): void {
    this.fetchConfigs();
    this.fetchJobs();
    // Poll for job updates
    interval(this.pollInterval)
      .pipe(takeUntil(this.destroy$))
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
    if (!this.loading) {
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
