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
              <div class="space-y-3 text-sm">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-gray-700">Cron:</span>
                  <code class="px-2 py-1 bg-gray-100 rounded text-gray-800">{{ cfg.schedule }}</code>
                </div>
                <div class="text-gray-800">
                  <span class="font-medium text-gray-700">Human:</span>
                  <span class="ml-2">{{ humanReadable[cfg.config_path] || '—' }}</span>
                </div>
                <div class="text-gray-800">
                  <span class="font-medium text-gray-700">Next Run:</span>
                  <span class="ml-2">{{ nextRunText[cfg.config_path] || 'Calculating...' }}</span>
                </div>
              </div>
            </div>
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
  humanReadable: Record<string, string> = {};
  nextRunText: Record<string, string> = {};
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
          this.computeDescriptions();
          this.loading = false;
        },
        error: (err: any) => {
          this.error = err?.error?.detail || 'Failed to load configs';
          this.loading = false;
        },
      });
  }

  private computeDescriptions(): void {
    for (const cfg of this.scheduledConfigs) {
      const cron = cfg.schedule || '';
      this.humanReadable[cfg.config_path] = this.describeCron(cron);
      this.nextRunText[cfg.config_path] = this.computeNextRun(cron);
    }
  }

  // Minimal 5-field cron parsing: supports '*' or comma-separated numbers per field.
  private parseCronField(field: string, min: number, max: number): Set<number> | null {
    if (field.trim() === '*') {
      const all = new Set<number>();
      for (let i = min; i <= max; i++) all.add(i);
      return all;
    }
    const out = new Set<number>();
    const parts = field.split(',').map(p => p.trim()).filter(Boolean);
    for (const p of parts) {
      const n = Number(p);
      if (Number.isFinite(n) && n >= min && n <= max) {
        out.add(n);
      }
    }
    return out.size > 0 ? out : null;
  }

  private matchesCron(date: Date, cron: string): boolean {
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return false;
    const [minF, hourF, domF, monF, dowF] = parts;
    const mins = this.parseCronField(minF, 0, 59);
    const hours = this.parseCronField(hourF, 0, 23);
    const dom = this.parseCronField(domF, 1, 31);
    const mon = this.parseCronField(monF, 1, 12);
    const dow = this.parseCronField(dowF, 0, 6);
    return (!!mins && mins.has(date.getMinutes())) &&
           (!!hours && hours.has(date.getHours())) &&
           (!!dom && dom.has(date.getDate())) &&
           (!!mon && mon.has(date.getMonth() + 1)) &&
           (!!dow && dow.has(date.getDay()));
  }

  private computeNextRun(cron: string): string {
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return 'Invalid cron';
    let cursor = new Date();
    // Start searching from the next minute
    cursor.setSeconds(0, 0);
    cursor = new Date(cursor.getTime() + 60000);
    for (let i = 0; i < 50000; i++) {
      if (this.matchesCron(cursor, cron)) {
        return cursor.toLocaleString();
      }
      cursor = new Date(cursor.getTime() + 60000);
    }
    return 'Not found soon';
  }

  private describeCron(cron: string): string {
    const parts = cron.trim().split(/\s+/);
    if (parts.length !== 5) return 'Invalid cron format';
    const [m, h, dom, mon, dow] = parts;
    const time = `${h === '*' ? 'every hour' : `at ${h.padStart(2, '0')}:${m.padStart(2, '0')}`}`;
    const day = dom === '*' ? (dow === '*' ? 'every day' : `on day-of-week ${dow}`) : `on day ${dom}`;
    const month = mon === '*' ? '' : ` in month ${mon}`;
    return `${time} ${day}${month}`.trim();
  }
}
