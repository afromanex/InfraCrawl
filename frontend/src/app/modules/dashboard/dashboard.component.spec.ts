import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { DashboardComponent } from './dashboard.component';
import { APIService } from '../../core/api/api.service';
import { ActiveCrawlRecord, CrawlRun, CrawlerConfig } from '../../core/models';

const mockConfigs: CrawlerConfig[] = [
  {
    config_id: 1,
    config_path: 'configs/a.yml',
    root_urls: ['https://a.example'],
    max_depth: 1,
    schedule: '0 2 * * *',
    resume_on_application_restart: true,
    fetch_mode: 'http',
    robots: true,
    refresh_days: 7,
  },
  {
    config_id: 2,
    config_path: 'configs/b.yml',
    root_urls: ['https://b.example'],
    max_depth: 2,
    schedule: null,
    resume_on_application_restart: true,
    fetch_mode: 'http',
    robots: true,
    refresh_days: null,
  },
  {
    config_id: 3,
    config_path: 'configs/c.yml',
    root_urls: ['https://c.example'],
    max_depth: 3,
    schedule: '0 3 * * *',
    resume_on_application_restart: true,
    fetch_mode: 'http',
    robots: true,
    refresh_days: 14,
  },
];

const mockActive: { active: ActiveCrawlRecord[] } = {
  active: [
    {
      id: 'c1',
      config_name: 'configs/a.yml',
      config_id: 1,
      status: 'running',
      started_at: '2026-01-17T00:00:00Z',
      last_seen: '2026-01-17T00:05:00Z',
      finished_at: null,
      pages_fetched: 120,
      links_found: 450,
      current_url: 'https://a.example/page',
      error: null,
    },
    {
      id: 'c2',
      config_name: 'configs/c.yml',
      config_id: 3,
      status: 'running',
      started_at: '2026-01-17T01:00:00Z',
      last_seen: '2026-01-17T01:05:00Z',
      finished_at: null,
      pages_fetched: 45,
      links_found: 90,
      current_url: 'https://c.example/page',
      error: null,
    },
  ],
};

const mockRuns: CrawlRun[] = [
  {
    run_id: 11,
    config_id: 1,
    config_path: 'configs/a.yml',
    start_timestamp: '2026-01-16T22:00:00Z',
    end_timestamp: '2026-01-16T22:30:00Z',
    exception: null,
    status: 'completed',
    pages_crawled: 300,
    current_depth: 2,
  },
  {
    run_id: 12,
    config_id: 2,
    config_path: 'configs/b.yml',
    start_timestamp: '2026-01-16T23:00:00Z',
    end_timestamp: null,
    exception: 'timeout',
    status: 'failed',
    pages_crawled: 10,
    current_depth: 1,
  },
];

describe('DashboardComponent', () => {
  let api: jasmine.SpyObj<APIService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<APIService>(
      'APIService',
      ['getConfigs', 'getActiveJobs', 'getJobRuns'],
    );
    api.getConfigs.and.returnValue(of(mockConfigs));
    api.getActiveJobs.and.returnValue(of(mockActive));
    api.getJobRuns.and.returnValue(of(mockRuns));

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [{ provide: APIService, useValue: api }],
    }).compileComponents();
  });

  it('loads summary metrics and renders them', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    expect(api.getConfigs).toHaveBeenCalled();
    expect(api.getActiveJobs).toHaveBeenCalled();
    expect(api.getJobRuns).toHaveBeenCalledWith(undefined, 5, 0);

    expect(compiled.querySelector('[data-testid="metric-configs"]')?.textContent).toContain('3');
    expect(compiled.querySelector('[data-testid="metric-scheduled"]')?.textContent).toContain('2');
    expect(compiled.querySelector('[data-testid="metric-unscheduled"]')?.textContent).toContain('1');
    expect(compiled.querySelector('[data-testid="metric-active"]')?.textContent).toContain('2');
  });

  it('shows active jobs and recent runs', () => {
    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    const activeItems = compiled.querySelectorAll('[data-testid="active-job-item"]');
    expect(activeItems.length).toBe(2);
    expect(activeItems[0].textContent).toContain('configs/a.yml');

    const runRows = compiled.querySelectorAll('[data-testid="recent-run-row"]');
    expect(runRows.length).toBe(2);
    expect(runRows[0].textContent).toContain('configs/a.yml');
  });
});
