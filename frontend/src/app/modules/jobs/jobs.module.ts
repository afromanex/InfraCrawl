import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { JobsComponent } from './jobs.component';
import { JobHistoryComponent } from './history/job-history.component';
import { ScheduleComponent } from './schedule/schedule.component';

const routes: Routes = [
  {
    path: 'active',
    component: JobsComponent,
  },
  {
    path: 'history',
    component: JobHistoryComponent,
  },
  {
    path: 'schedule',
    component: ScheduleComponent,
  },
  {
    path: '',
    redirectTo: 'active',
    pathMatch: 'full',
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes), JobsComponent, JobHistoryComponent, ScheduleComponent],
})
export class JobsModule {}
