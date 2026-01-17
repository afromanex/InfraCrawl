import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.css'],
})
export class SidebarComponent {
  menuItems = [
    { label: 'Dashboard', route: '/dashboard', icon: 'dashboard' },
    { label: 'Configurations', route: '/configs', icon: 'settings' },
    { label: 'Active Jobs', route: '/jobs/active', icon: 'play_circle' },
    { label: 'Job History', route: '/jobs/history', icon: 'history' },
    { label: 'Admin', route: '/admin', icon: 'admin_panel_settings' },
  ];
}
