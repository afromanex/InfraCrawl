import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { forkJoin, Subject, takeUntil } from 'rxjs';
import { APIService } from '../../core/api/api.service';
import { CrawlerConfig } from '../../core/models';

@Component({
  selector: 'app-configs',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Configurations</h1>

      <div *ngIf="loading" class="text-gray-600">Loading configurations...</div>

      <div *ngIf="error" class="rounded-md bg-red-50 p-3 text-sm text-red-800 mb-4">
        {{ error }}
      </div>

      <div *ngIf="statsError" class="rounded-md bg-yellow-50 p-3 text-sm text-yellow-800 mb-4">
        {{ statsError }}
      </div>

      <div *ngIf="statsLoading && configs.length > 0" class="text-gray-600 mb-2 text-sm">
        Loading stats for configurations...
      </div>

      <div *ngIf="!loading && !error && configs.length === 0" class="text-gray-600">
        No configurations found.
      </div>

      <div *ngIf="configs.length > 0" class="overflow-hidden rounded-lg shadow ring-1 ring-black ring-opacity-5">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Path
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Pages
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Links
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <ng-container *ngFor="let cfg of configs">
              <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ cfg.config_id }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ cfg.config_path }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ cfg.pages_count ?? '—' }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ cfg.links_count ?? '—' }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <div class="flex gap-2">
                    <button
                      type="button"
                      class="px-3 py-1 text-sm text-primary-600 hover:text-primary-800 hover:bg-primary-50 rounded"
                      (click)="toggleConfig(cfg.config_path)"
                    >
                      {{ expanded.has(cfg.config_path) ? 'Hide' : 'View' }}
                    </button>
                    <button
                      type="button"
                      class="px-3 py-1 text-sm text-white bg-red-600 hover:bg-red-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                      (click)="clearConfigData(cfg.config_path)"
                      [disabled]="clearingConfigs.has(cfg.config_path)"
                    >
                      {{ clearingConfigs.has(cfg.config_path) ? 'Clearing...' : 'Clear Data' }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr *ngIf="expanded.has(cfg.config_path)">
                <td colspan="5" class="px-6 py-4 bg-gray-50 text-sm text-gray-800">
                  <div *ngIf="configContentLoading.has(cfg.config_path)" class="text-gray-600">Loading config...</div>
                  <div *ngIf="configContentError.get(cfg.config_path)" class="text-red-700">
                    {{ configContentError.get(cfg.config_path) }}
                  </div>
                  <pre
                    *ngIf="configContent.get(cfg.config_path)"
                    class="bg-white border border-gray-200 rounded p-3 overflow-auto text-xs leading-5"
                  >
{{ configContent.get(cfg.config_path) }}
                  </pre>
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
export class ConfigsComponent implements OnInit, OnDestroy {
  configs: Array<CrawlerConfig & { pages_count?: number; links_count?: number }> = [];
  loading = false;
  error: string | null = null;
  statsError: string | null = null;
  statsLoading = false;
  expanded = new Set<string>();
  clearingConfigs = new Set<string>();
  configContent = new Map<string, string>();
  configContentLoading = new Set<string>();
  configContentError = new Map<string, string>();
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
    this.statsError = null;

    this.api
      .getConfigs()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (cfgs) => {
          this.configs = cfgs;
          this.loading = false;
          this.fetchStats(cfgs);
        },
        error: (err) => {
          this.error = err?.error?.detail || 'Failed to load configurations';
          this.loading = false;
        },
      });
  }

  private fetchStats(cfgs: CrawlerConfig[]): void {
    if (cfgs.length === 0) {
      this.loading = false;
      return;
    }

    const statsCalls = cfgs.map((cfg) => this.api.getJobStats(cfg.config_path));

    this.statsLoading = true;
    forkJoin(statsCalls)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (statsArr: { config_path: string; pages: number; links: number }[]) => {
          const statsByPath = new Map<string, { pages: number; links: number }>();
          statsArr.forEach((s) => statsByPath.set(s.config_path, { pages: s.pages, links: s.links }));
          this.configs = this.configs.map((c) => {
            const stats = statsByPath.get(c.config_path);
            return {
              ...c,
              pages_count: stats?.pages,
              links_count: stats?.links,
            };
          });
          this.statsLoading = false;
        },
        error: (err) => {
          this.statsError = err?.error?.detail || 'Failed to load configuration stats';
          this.statsLoading = false;
        },
      });
  }

  toggleConfig(configPath: string): void {
    if (this.expanded.has(configPath)) {
      this.expanded.delete(configPath);
      return;
    }

    this.expanded.add(configPath);

    if (this.configContent.has(configPath) || this.configContentLoading.has(configPath)) {
      return;
    }

    this.configContentLoading.add(configPath);
    this.api
      .getConfig(configPath)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (content: string) => {
          this.configContent.set(configPath, content);
          this.configContentLoading.delete(configPath);
        },
        error: (err) => {
          this.configContentError.set(
            configPath,
            err?.error?.detail || 'Failed to load config file'
          );
          this.configContentLoading.delete(configPath);
        },
      });
  }

  clearConfigData(configPath: string): void {
    if (!confirm(`Clear all crawler data for ${configPath}? This cannot be undone.`)) {
      return;
    }

    this.clearingConfigs.add(configPath);
    this.api
      .removeConfigData(configPath)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.clearingConfigs.delete(configPath);
          this.fetchConfigs(); // Refresh to update stats
        },
        error: (err: any) => {
          this.clearingConfigs.delete(configPath);
          this.error = err?.error?.detail || 'Failed to clear config data';
        },
      });
  }
}
