import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './modules/auth/login/login.component';
import { LayoutComponent } from './modules/layout/layout.component';
import { AuthGuard } from './core/auth/auth.guard';

const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent,
  },
  {
    path: '',
    component: LayoutComponent,
    canActivate: [AuthGuard],
    children: [
      {
        path: 'dashboard',
        loadChildren: () =>
          import('./modules/dashboard/dashboard.module').then(
            (m) => m.DashboardModule
          ),
      },
      {
        path: 'configs',
        loadChildren: () =>
          import('./modules/configs/configs.module').then(
            (m) => m.ConfigsModule
          ),
      },
      {
        path: 'jobs',
        loadChildren: () =>
          import('./modules/jobs/jobs.module').then((m) => m.JobsModule),
      },
      {
        path: 'admin',
        loadChildren: () =>
          import('./modules/admin/admin.module').then((m) => m.AdminModule),
      },
      {
        path: '',
        redirectTo: '/dashboard',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: '',
    redirectTo: '/login',
    pathMatch: 'full',
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
