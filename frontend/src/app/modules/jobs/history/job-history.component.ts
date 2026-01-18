import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { takeUntil, Subject } from 'rxjs';
import { APIService } from '../../../core/api/api.service';
import { CrawlRun } from '../../../core/models';

@Component({
  selector: 'app-job-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Job History</h1>


      <div *ngIf="loading" class="text-gray-600">Loading job history...</div>
      <div *ngIf="error" class="rounded-md bg-red-50 p-3 text-sm text-red-800 mb-4">{{ error }}</div>

      <div *ngIf="!loading && runs.length === 0" class="text-gray-600">No runs found.</div>

      <div *ngIf="runs.length > 0" class="overflow-hidden rounded-lg shadow ring-1 ring-black ring-opacity-5">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Run ID</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Config</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">End</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Exception</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr *ngFor="let r of runs">
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ r.run_id }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ r.config_path || r.config_id }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <span [ngClass]="getStatusClass(r.status)">{{ r.status }}</span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatTime(r.start_timestamp) }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ formatTime(r.end_timestamp) }}</td>
              <td class="px-6 py-4 text-xs">
                <pre class="max-w-xl overflow-x-auto whitespace-pre-wrap break-words" *ngIf="r.exception">{{ r.exception }}</pre>
                <span *ngIf="!r.exception" class="text-gray-500">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex items-center gap-2 mt-4" *ngIf="runs.length > 0">
        <button
          type="button"
          class="px-3 py-1 bg-gray-100 text-gray-800 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          [disabled]="offset === 0 || loading"
          (click)="prevPage()"
        >
          Previous
        </button>
        <span class="text-sm text-gray-600">Page {{ (offset / limit) + 1 }}</span>
        <button
          type="button"
          class="px-3 py-1 bg-gray-100 text-gray-800 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          [disabled]="runs.length < limit || loading"
          (click)="nextPage()"
        >
          Next
        </button>
      </div>
    </div>
  `,
  styles: [],
})
export class JobHistoryComponent implements OnInit, OnDestroy {
  runs: CrawlRun[] = [];
  loading = false;
  error: string | null = null;
  limit = 10;
  offset = 0;
  private destroy$ = new Subject<void>();

  constructor(private api: APIService) {}

  ngOnInit(): void {
    this.fetchRuns();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  prevPage(): void {
    if (this.offset === 0) return;
    this.offset = Math.max(0, this.offset - this.limit);
    this.fetchRuns();
  }

  nextPage(): void {
    this.offset += this.limit;
    this.fetchRuns();
  }

  private fetchRuns(): void {
    this.loading = true;
    this.error = null;
    this.api
      .getJobRuns(undefined, this.limit, this.offset)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (runs: CrawlRun[]) => {
          this.runs = runs || [];
          this.loading = false;
        },
        error: (err: any) => {
          this.error = err?.error?.detail || 'Failed to load job history';
          this.loading = false;
        },
      });
  }

  getStatusClass(status: string): string {
    const base = 'px-2 py-1 rounded-full text-xs font-semibold';
    switch (status) {
      case 'running':
        return base + ' bg-blue-100 text-blue-800';
      case 'completed':
        return base + ' bg-green-100 text-green-800';
      case 'failed':
        return base + ' bg-red-100 text-red-800';
      case 'stopped':
        return base + ' bg-yellow-100 text-yellow-800';
      default:
        return base + ' bg-gray-100 text-gray-800';
    }
  }

  formatTime(timestamp: string | null): string {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return date.toLocaleString();
  }
}
