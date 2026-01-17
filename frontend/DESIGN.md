# InfraCrawl Frontend Design Document

## Overview

Angular SPA for managing web crawlers with the following goals:
- Authenticate and authorize users
- View and manage crawler configurations
- Monitor active and historical crawl jobs
- Control crawler execution (start, stop, resume)
- Administer system settings and logs

## Technology Stack

- **Framework**: Angular (latest LTS)
- **Styling**: Tailwind CSS
- **State Management**: RxJS services (facade pattern over domain services)
- **HTTP Client**: Angular HttpClient with interceptors
- **Authentication**: Token-based (JWT in localStorage)

---

## Component Hierarchy

```
AppComponent (root)
├── AuthModule
│   ├── LoginComponent
│   └── AuthGuard (route protection)
│
├── LayoutComponent (after auth)
│   ├── NavbarComponent
│   ├── SidebarComponent
│   └── MainComponent
│       ├── Dashboard
│       ├── ConfigsComponent
│       │   ├── ConfigListComponent
│       │   └── ConfigDetailComponent
│       ├── JobsComponent
│       │   ├── ActiveJobsComponent
│       │   │   └── JobStatusCardComponent
│       │   ├── JobHistoryComponent
│       │   │   └── JobHistoryTableComponent
│       │   └── JobDetailComponent
│       └── AdminComponent
│           ├── SystemLogsComponent
│           ├── SettingsComponent
│           └── StatsComponent
```

---

## Data Flow Architecture

### Service Layer (State Management)

```
API Layer (HttpClient)
    ↓
APIService (auth, crawlers, jobs, configs)
    ↓
Facade Services (RxJS Observables)
    ├── AuthFacade
    ├── ConfigFacade
    ├── JobFacade
    └── SystemFacade
    ↓
Components (subscribe to observables, dispatch actions)
```

### State Management Pattern

Use **RxJS services with behavior subjects** for clean, reactive state:

```typescript
// Example: ConfigFacade
export class ConfigFacade {
  private configsSubject = new BehaviorSubject<CrawlerConfig[]>([]);
  configs$ = this.configsSubject.asObservable();
  
  private loadingSubject = new BehaviorSubject<boolean>(false);
  loading$ = this.loadingSubject.asObservable();
  
  constructor(private api: APIService) {}
  
  loadConfigs() {
    this.loadingSubject.next(true);
    this.api.getConfigs().subscribe({
      next: (configs) => this.configsSubject.next(configs),
      error: (err) => console.error(err),
      finalize: () => this.loadingSubject.next(false)
    });
  }
}
```

Benefits:
- ✅ No Redux/NgRx boilerplate
- ✅ Services own their state
- ✅ Components stay simple
- ✅ Easy to test

---

## User Workflows

### Workflow 1: Sign In
1. User navigates to `/login`
2. Enters email and password
3. System calls `POST /api/auth/login`
4. JWT token stored in localStorage
5. Redirect to Dashboard
6. AuthGuard protects all other routes

### Workflow 2: View Configurations
1. User navigates to `/configs`
2. ConfigListComponent loads all configs via ConfigFacade
3. Displays table: Config Name | Root URLs | Max Depth | Fetch Mode | Schedule
4. User can click config to view details in ConfigDetailComponent
5. Details show full YAML, edit option (future), stats

### Workflow 3: View Active Jobs
1. User navigates to Dashboard or `/jobs/active`
2. ActiveJobsComponent fetches running jobs
3. Displays real-time job cards:
   - Config name, start time, pages crawled, current depth
   - Progress bar (pages crawled / estimated)
4. Auto-refresh every 2-5 seconds (WebSocket ideal, but polling for MVP)
5. Click card to view job details (depth breakdown, links found, errors)

### Workflow 4: View Job History
1. User navigates to `/jobs/history`
2. JobHistoryComponent displays paginated table
3. Columns: Config | Start | End | Status | Pages | Links | Errors
4. Filter by config, date range, status
5. Click row to expand detailed view (logs, page samples)

### Workflow 5: Control Execution
1. From Active Jobs or detail view, user can:
   - **Stop**: `POST /api/crawlers/{config_id}/stop` → marks run as stopped
   - **Resume**: `POST /api/crawlers/{config_id}/resume` → restarts paused crawl
   - **Delete Data**: `DELETE /api/crawlers/{config_id}/data` → clears crawled pages/links
2. Confirmation modal before destructive operations
3. Toast notification on success/error

### Workflow 6: Admin Functions
1. User with admin role navigates to `/admin`
2. Views:
   - System stats (total configs, total runs, DB size estimate)
   - Crawl logs (tail, filter by config/level)
   - Settings (log retention, timeout limits, etc.)
3. Can clear old logs, restart service (future)

---

## API Contracts

### Authentication
```
POST /api/auth/login
{ email, password }
→ { access_token, expires_in }

GET /api/auth/me
→ { user_id, email, role, permissions }
```

### Configs
```
GET /api/crawlers/configs
→ [{ config_id, config_path, schedule, resume_on_application_restart, ... }]

GET /api/crawlers/configs/{config_id}
→ { full config object with root_urls, fetch_mode, etc. }
```

### Jobs
```
GET /api/crawlers/active
→ [{ run_id, config_id, config_path, start_timestamp, pages_crawled, current_depth, status }]

GET /api/crawlers/runs?config_id={id}&limit={n}&offset={offset}
→ [{ run_id, config_path, start_timestamp, end_timestamp, status, pages_crawled, ... }]

GET /api/crawlers/runs/{run_id}
→ { detailed run info + page/link samples }

POST /api/crawlers/{config_id}/stop
POST /api/crawlers/{config_id}/resume
DELETE /api/crawlers/{config_id}/data
```

### Admin
```
GET /api/admin/stats
→ { total_configs, total_runs, db_size, active_jobs_count }

GET /api/admin/logs?level={INFO|ERROR|DEBUG}&config_id={id}&tail={n}
→ [{ timestamp, level, message, config_id }]
```

---

## Build Phases

### Phase 1: Authentication & Layout
**Goal**: Set up auth flow, layout shell, navigation

**Components**:
- LoginComponent
- LayoutComponent (navbar, sidebar)
- AuthGuard + token interceptor

**Services**:
- AuthService (login, logout, token storage)
- AuthFacade (currentUser$, isAuthenticated$)

**Success Criteria**:
- ✅ User can log in with credentials
- ✅ Token stored and sent with all requests
- ✅ Protected routes redirect to login
- ✅ Logout clears state

---

### Phase 2: Display Configurations
**Goal**: List all crawler configs

**Components**:
- ConfigListComponent (table)
- ConfigDetailComponent (detail view)

**Services**:
- APIService.getConfigs()
- ConfigFacade (configs$, selectedConfig$)

**Success Criteria**:
- ✅ List all configs in table format
- ✅ Click config to view details
- ✅ Show config metadata (path, schedule, root URLs)

---

### Phase 3: Display Running Jobs
**Goal**: Real-time view of active crawls

**Components**:
- ActiveJobsComponent (dashboard view)
- JobStatusCardComponent (reusable card)

**Services**:
- APIService.getActiveJobs()
- JobFacade (activeJobs$, auto-refresh)

**Success Criteria**:
- ✅ Poll `/api/crawlers/active` every 3 seconds
- ✅ Display job status cards with progress bars
- ✅ Show pages crawled, current depth, elapsed time
- ✅ Click to view detailed job info

---

### Phase 4: Display All Jobs (History)
**Goal**: Browse past and current job records

**Components**:
- JobHistoryComponent (table with pagination/filters)
- JobHistoryTableComponent (reusable table)
- JobDetailExpandComponent (inline expansion)

**Services**:
- APIService.getJobRuns(config_id, limit, offset)
- JobFacade.loadHistory(filters)

**Success Criteria**:
- ✅ Paginated job history table
- ✅ Filter by config, date range, status
- ✅ Expand row to see details + error logs
- ✅ Search by config name

---

### Phase 5: Integrating Controls
**Goal**: Allow users to start/stop/resume/delete

**Components**:
- Add control buttons to ActiveJobsComponent, JobDetailComponent
- ConfirmDialogComponent (reusable modal)
- ToastNotificationComponent (success/error messages)

**Services**:
- APIService.stopCrawl(config_id)
- APIService.resumeCrawl(config_id)
- APIService.deleteCrawlData(config_id)

**Success Criteria**:
- ✅ Stop button halts running job
- ✅ Resume button restarts paused job
- ✅ Delete clears pages/links with confirmation
- ✅ Toast notifications on success/error
- ✅ UI updates reflect changes

---

### Phase 6: Administrative Functions
**Goal**: System monitoring and management

**Components**:
- AdminComponent (layout)
- SystemStatsComponent (metrics dashboard)
- CrawlLogsComponent (log viewer/search)
- SettingsComponent (future: config system settings)

**Services**:
- APIService.getSystemStats()
- APIService.getLogs(filter)

**Success Criteria**:
- ✅ Display system stats (total configs, runs, DB size)
- ✅ View crawl logs with filtering
- ✅ Search logs by config, timestamp, level
- ✅ Role-based access (admin only)

---

## Folder Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── core/
│   │   │   ├── auth/
│   │   │   │   ├── auth.service.ts
│   │   │   │   ├── auth.guard.ts
│   │   │   │   └── auth.interceptor.ts
│   │   │   ├── api/
│   │   │   │   ├── api.service.ts
│   │   │   │   └── models/
│   │   │   └── facades/
│   │   │       ├── auth.facade.ts
│   │   │       ├── config.facade.ts
│   │   │       ├── job.facade.ts
│   │   │       └── system.facade.ts
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   │   ├── login/
│   │   │   │   └── auth.module.ts
│   │   │   ├── layout/
│   │   │   │   ├── navbar/
│   │   │   │   ├── sidebar/
│   │   │   │   └── layout.module.ts
│   │   │   ├── configs/
│   │   │   │   ├── config-list/
│   │   │   │   ├── config-detail/
│   │   │   │   └── configs.module.ts
│   │   │   ├── jobs/
│   │   │   │   ├── active-jobs/
│   │   │   │   ├── job-history/
│   │   │   │   ├── job-detail/
│   │   │   │   └── jobs.module.ts
│   │   │   ├── admin/
│   │   │   │   ├── stats/
│   │   │   │   ├── logs/
│   │   │   │   └── admin.module.ts
│   │   ├── shared/
│   │   │   ├── components/
│   │   │   │   ├── confirm-dialog/
│   │   │   │   ├── toast/
│   │   │   │   └── job-status-card/
│   │   │   └── shared.module.ts
│   │   ├── app.component.ts
│   │   └── app.module.ts
│   ├── assets/
│   ├── styles/
│   │   └── tailwind.css
│   └── main.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## Next Steps

1. **Scaffold Angular project** with Tailwind setup
2. **Phase 1**: Auth module + token interceptor
3. **Phase 2**: Config listing and detail views
4. Continue iteratively through phases 3-6

