import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject, takeUntil, interval } from 'rxjs';
import { APIService } from '../../core/api/api.service';

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
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Active Jobs</h1>

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
                Pages Fetched
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Links Found
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
  loading = false;
  error: string | null = null;
  expanded = new Set<string>();
  private destroy$ = new Subject<void>();
  private pollInterval = 5000; // Poll every 5 seconds

  constructor(private api: APIService) {}

  ngOnInit(): void {
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
