import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ActiveJobsComponent } from './active/active-jobs.component';
import { JobHistoryComponent } from './history/job-history.component';

const routes: Routes = [
  {
    path: 'active',
    component: ActiveJobsComponent,
  },
  {
    path: 'history',
    component: JobHistoryComponent,
  },
  {
    path: '',
    redirectTo: 'active',
    pathMatch: 'full',
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes), ActiveJobsComponent, JobHistoryComponent],
})
export class JobsModule {}
