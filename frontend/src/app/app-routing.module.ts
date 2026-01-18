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
        loadComponent: () =>
          import('./modules/dashboard/dashboard.component').then(
            (m) => m.DashboardComponent
          ),
      },
      {
        path: 'configs',
        loadComponent: () =>
          import('./modules/configs/configs.component').then(
            (m) => m.ConfigsComponent
          ),
      },
      {
        path: 'jobs',
        loadChildren: () =>
          import('./modules/jobs/jobs.module').then((m) => m.JobsModule),
      },
      {
        path: 'admin',
        loadComponent: () =>
          import('./modules/admin/admin.component').then((m) => m.AdminComponent),
      },
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: '**',
    redirectTo: '/login',
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
