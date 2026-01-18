import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject, takeUntil } from 'rxjs';
import { APIService } from '../../../core/api/api.service';
import { CrawlerConfig } from '../../../core/models';

@Component({
  selector: 'app-schedule',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Crawl Schedules</h1>
      <p class="text-gray-600 mb-6">Configure and view scheduled crawl jobs.</p>

      <div *ngIf="loading" class="text-gray-600">Loading schedules...</div>
      <div *ngIf="error" class="rounded-md bg-red-50 p-3 text-sm text-red-800 mb-4">{{ error }}</div>

      <div *ngIf="!loading && scheduledConfigs.length === 0" class="text-gray-600">
        No scheduled crawls configured.
      </div>

      <div *ngIf="scheduledConfigs.length > 0" class="space-y-4">
        <div *ngFor="let cfg of scheduledConfigs" class="bg-white rounded-lg shadow p-6">
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-gray-900 mb-2">{{ cfg.config_path }}</h3>
              <div class="space-y-2 text-sm">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-700">Schedule:</span>
                  <code class="px-2 py-1 bg-gray-100 rounded text-gray-800">{{ cfg.schedule }}</code>
                  <span class="text-gray-500">(cron format)</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-700">Max Depth:</span>
                  <span class="text-gray-900">{{ cfg.max_depth }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-700">Fetch Mode:</span>
                  <span class="text-gray-900">{{ cfg.fetch_mode }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-700">Resume on Restart:</span>
                  <span [class]="cfg.resume_on_application_restart ? 'text-green-600' : 'text-gray-500'">
                    {{ cfg.resume_on_application_restart ? 'Yes' : 'No' }}
                  </span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-700">Root URLs:</span>
                  <span class="text-gray-900">{{ cfg.root_urls.length }} URL(s)</span>
                </div>
              </div>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200">
            <details class="text-sm">
              <summary class="cursor-pointer text-blue-600 hover:text-blue-800">Show root URLs</summary>
              <ul class="mt-2 space-y-1 pl-4">
                <li *ngFor="let url of cfg.root_urls" class="text-gray-700 font-mono text-xs break-all">{{ url }}</li>
              </ul>
            </details>
          </div>
        </div>
      </div>

      <div *ngIf="!loading && configs.length > 0 && scheduledConfigs.length < configs.length" class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 class="text-sm font-semibold text-blue-900 mb-2">Unscheduled Configs</h3>
        <p class="text-sm text-blue-800 mb-2">The following configs have no schedule set:</p>
        <ul class="text-sm text-blue-700 space-y-1">
          <li *ngFor="let cfg of unscheduledConfigs" class="font-mono">{{ cfg.config_path }}</li>
        </ul>
        <p class="text-xs text-blue-600 mt-2">To schedule these, add a <code class="bg-blue-100 px-1 rounded">schedule</code> field in the YAML config file.</p>
      </div>
    </div>
  `,
  styles: [],
})
export class ScheduleComponent implements OnInit, OnDestroy {
  configs: CrawlerConfig[] = [];
  scheduledConfigs: CrawlerConfig[] = [];
  unscheduledConfigs: CrawlerConfig[] = [];
  loading = false;
  error: string | null = null;
  private destroy$ = new Subject<void>();

  constructor(private api: APIService) {}

  ngOnInit(): void {
    this.fetchConfigs();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private fetchConfigs(): void {
    this.loading = true;
    this.error = null;
    this.api
      .getConfigs()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (configs: CrawlerConfig[]) => {
          this.configs = configs;
          this.scheduledConfigs = configs.filter(c => c.schedule && c.schedule.trim() !== '');
          this.unscheduledConfigs = configs.filter(c => !c.schedule || c.schedule.trim() === '');
          this.loading = false;
        },
        error: (err: any) => {
          this.error = err?.error?.detail || 'Failed to load configs';
          this.loading = false;
        },
      });
  }
}
