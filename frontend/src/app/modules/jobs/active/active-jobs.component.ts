import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-active-jobs',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Active Jobs</h1>
      <p class="text-gray-600">View currently running crawl jobs.</p>
    </div>
  `,
  styles: [],
})
export class ActiveJobsComponent {}
