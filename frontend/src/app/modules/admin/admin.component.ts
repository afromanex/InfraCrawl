import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">Admin</h1>
      <p class="text-gray-600">System administration and settings.</p>
    </div>
  `,
  styles: [],
})
export class AdminComponent {}
