import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ConfigsComponent } from './configs.component';

const routes: Routes = [
  {
    path: '',
    component: ConfigsComponent,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes), ConfigsComponent],
})
export class ConfigsModule {}
