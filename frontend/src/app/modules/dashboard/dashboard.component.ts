import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Subject, takeUntil, forkJoin } from 'rxjs';
import { APIService } from '../../core/api/api.service';
import { CrawlerConfig, CrawlRun, ActiveCrawlRecord } from '../../core/models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div *ngIf="loading" class="text-gray-600">Loading dashboard data...</div>
      <div *ngIf="error" class="rounded-md bg-red-50 p-3 text-sm text-red-800 mb-4">{{ error }}</div>

      <div *ngIf="!loading && !error" class="space-y-6">
        <!-- Metrics Cards -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-1">
                  <dt class="text-sm font-medium text-gray-500 truncate">Total Configs</dt>
                  <dd class="mt-1 text-3xl font-semibold text-gray-900" data-testid="metric-configs">{{ totalConfigs }}</dd>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-1">
                  <dt class="text-sm font-medium text-gray-500 truncate">Scheduled</dt>
                  <dd class="mt-1 text-3xl font-semibold text-green-600" data-testid="metric-scheduled">{{ scheduledCount }}</dd>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-1">
                  <dt class="text-sm font-medium text-gray-500 truncate">Unscheduled</dt>
                  <dd class="mt-1 text-3xl font-semibold text-gray-600" data-testid="metric-unscheduled">{{ unscheduledCount }}</dd>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
              <div class="flex items-center">
                <div class="flex-1">
                  <dt class="text-sm font-medium text-gray-500 truncate">Active Crawls</dt>
                  <dd class="mt-1 text-3xl font-semibold text-blue-600" data-testid="metric-active">{{ activeCount }}</dd>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Active Crawls Section -->
        <div class="bg-white shadow rounded-lg">
          <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
            <h2 class="text-lg font-medium text-gray-900">Active Crawls</h2>
          </div>
          <div class="px-4 py-5 sm:p-6">
            <div *ngIf="activeJobs.length === 0" class="text-gray-500 text-sm">No active crawls</div>
            <ul *ngIf="activeJobs.length > 0" class="space-y-3">
              <li *ngFor="let job of activeJobs" class="flex items-center justify-between" data-testid="active-job-item">
                <div class="flex-1">
                  <div class="text-sm font-medium text-gray-900">{{ job.config_name }}</div>
                  <div class="text-xs text-gray-500">
                    Started: {{ formatTime(job.started_at) }} • 
                    Pages: {{ job.pages_fetched }} • 
                    Links: {{ job.links_found }}
                  </div>
                </div>
                <a [routerLink]="['/jobs/active']" class="text-sm text-blue-600 hover:text-blue-800">View</a>
              </li>
            </ul>
          </div>
        </div>

        <!-- Recent Runs Section -->
        <div class="bg-white shadow rounded-lg">
          <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-medium text-gray-900">Recent Runs</h2>
              <a [routerLink]="['/jobs/history']" class="text-sm text-blue-600 hover:text-blue-800">View All</a>
            </div>
          </div>
          <div class="px-4 py-5 sm:p-6">
            <div *ngIf="recentRuns.length === 0" class="text-gray-500 text-sm">No recent runs</div>
            <div *ngIf="recentRuns.length > 0" class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th class="text-left text-xs font-medium text-gray-500 uppercase">Config</th>
                    <th class="text-left text-xs font-medium text-gray-500 uppercase">Start</th>
                    <th class="text-left text-xs font-medium text-gray-500 uppercase">End</th>
                    <th class="text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                  <tr *ngFor="let run of recentRuns" class="text-sm" data-testid="recent-run-row">
                    <td class="py-2 text-gray-900">{{ run.config_path || run.config_id }}</td>
                    <td class="py-2 text-gray-900">{{ formatTime(run.start_timestamp) }}</td>
                    <td class="py-2 text-gray-900">{{ formatTime(run.end_timestamp) }}</td>
                    <td class="py-2">
                      <span *ngIf="run.end_timestamp && !run.exception" class="text-green-600">Completed</span>
                      <span *ngIf="run.exception" class="text-red-600">Failed</span>
                      <span *ngIf="!run.end_timestamp" class="text-gray-500">Running</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="bg-white shadow rounded-lg">
          <div class="px-4 py-5 sm:px-6 border-b border-gray-200">
            <h2 class="text-lg font-medium text-gray-900">Quick Actions</h2>
          </div>
          <div class="px-4 py-5 sm:p-6">
            <div class="flex flex-wrap gap-3">
              <a [routerLink]="['/configs']" class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                View Configs
              </a>
              <a [routerLink]="['/jobs/schedule']" class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                Manage Schedules
              </a>
              <a [routerLink]="['/jobs/active']" class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                Active Jobs
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [],
})
export class DashboardComponent implements OnInit, OnDestroy {
  configs: CrawlerConfig[] = [];
  activeJobs: ActiveCrawlRecord[] = [];
  recentRuns: CrawlRun[] = [];

  totalConfigs = 0;
  scheduledCount = 0;
  unscheduledCount = 0;
  activeCount = 0;

  loading = false;
  error: string | null = null;

  private destroy$ = new Subject<void>();

  constructor(private api: APIService) {}

  ngOnInit(): void {
    this.loadDashboard();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadDashboard(): void {
    this.loading = true;
    this.error = null;

    forkJoin({
      configs: this.api.getConfigs(),
      active: this.api.getActiveJobs(),
      runs: this.api.getJobRuns(undefined, 5, 0),
    })
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (result) => {
          this.configs = result.configs || [];
          this.activeJobs = result.active?.active || [];
          this.recentRuns = result.runs || [];

          this.totalConfigs = this.configs.length;
          this.scheduledCount = this.configs.filter(c => c.schedule && c.schedule.trim() !== '').length;
          this.unscheduledCount = this.totalConfigs - this.scheduledCount;
          this.activeCount = this.activeJobs.length;

          this.loading = false;
        },
        error: (err: any) => {
          this.error = err?.error?.detail || 'Failed to load dashboard data';
          this.loading = false;
        },
      });
  }

  formatTime(timestamp: string | null): string {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return date.toLocaleString();
  }
}
