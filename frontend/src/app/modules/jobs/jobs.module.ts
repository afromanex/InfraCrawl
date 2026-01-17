import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { JobsComponent } from './jobs.component';
import { JobHistoryComponent } from './history/job-history.component';

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
    path: '',
    redirectTo: 'active',
    pathMatch: 'full',
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes), JobsComponent, JobHistoryComponent],
})
export class JobsModule {}
