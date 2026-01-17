import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-job-history',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Job History</h1>
      <p class="text-gray-600">View completed and failed crawl jobs.</p>
    </div>
  `,
  styles: [],
})
export class JobHistoryComponent {}
