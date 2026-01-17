import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-configs',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Configurations</h1>
      <p class="text-gray-600">Manage your crawler configurations here.</p>
    </div>
  `,
  styles: [],
})
export class ConfigsComponent {}
