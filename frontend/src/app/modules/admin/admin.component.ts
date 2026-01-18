import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { APIService } from '../../core/api/api.service';

interface ConfigEntry {
  key: string;
  value: string | null;
  description: string;
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-6">System</h1>
      
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 class="text-xl font-semibold text-gray-800">Configuration</h2>
          <p class="text-sm text-gray-600 mt-1">Current runtime environment settings</p>
        </div>
        
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Variable</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr *ngFor="let entry of configEntries" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">{{ entry.key }}</td>
                <td class="px-6 py-4 text-sm text-gray-700">
                  <span *ngIf="entry.key === 'DATABASE_URL' && entry.value" class="text-gray-500 italic">
                    {{ maskDatabaseUrl(entry.value) }}
                  </span>
                  <span *ngIf="entry.key !== 'DATABASE_URL' || !entry.value" [class.text-gray-400]="!entry.value" [class.italic]="!entry.value">
                    {{ entry.value || '(not set)' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm text-gray-600">{{ entry.description }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div *ngIf="error" class="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
        <p class="text-red-800">{{ error }}</p>
      </div>
    </div>
  `,
  styles: [],
})
export class AdminComponent implements OnInit {
  configEntries: ConfigEntry[] = [];
  error: string = '';

  private descriptions: Record<string, string> = {
    'DATABASE_URL': 'PostgreSQL connection string',
    'USER_AGENT': 'User-Agent header for HTTP requests',
    'HTTP_TIMEOUT': 'Timeout for outbound HTTP requests (seconds)',
    'CRAWL_DELAY': 'Politeness delay between page fetches (seconds)',
    'INFRACRAWL_CONFIG_WATCH_INTERVAL': 'Config polling interval (seconds)',
    'INFRACRAWL_RECOVERY_MODE': 'Startup behavior for incomplete runs',
    'INFRACRAWL_RECOVERY_WITHIN_SECONDS': 'Recovery time window (seconds)',
    'INFRACRAWL_RECOVERY_MESSAGE': 'Message logged during recovery',
    'INFRACRAWL_VISITED_MAX_URLS': 'Max URLs tracked per crawl',
    'INFRACRAWL_ROBOTS_CACHE_MAX_SIZE': 'Max robots.txt cache entries',
    'INFRACRAWL_ROBOTS_CACHE_TTL_SECONDS': 'robots.txt cache TTL (seconds)',
  };

  constructor(private api: APIService) {}

  ngOnInit() {
    this.loadConfig();
  }

  loadConfig() {
    this.api.getSystemConfig().subscribe({
      next: (response) => {
        this.configEntries = Object.entries(response.environment).map(([key, value]) => ({
          key,
          value,
          description: this.descriptions[key] || '',
        }));
      },
      error: (err) => {
        this.error = 'Failed to load system configuration';
        console.error('Failed to load config:', err);
      },
    });
  }

  maskDatabaseUrl(url: string): string {
    // Mask password in DATABASE_URL for security
    return url.replace(/(:\/\/[^:]+:)([^@]+)(@)/, '$1****$3');
  }
}

