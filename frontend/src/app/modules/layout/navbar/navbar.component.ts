import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthFacade } from '../../../core/facades/auth.facade';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './navbar.component.html',
  styleUrls: ['./navbar.component.css'],
})
export class NavbarComponent {
  @Output() toggleSidebar = new EventEmitter<void>();

  currentUser$ = this.authFacade.currentUser$;
  userMenuOpen = false;

  constructor(private authFacade: AuthFacade) {}

  onToggleSidebar(): void {
    this.toggleSidebar.emit();
  }

  toggleUserMenu(): void {
    this.userMenuOpen = !this.userMenuOpen;
  }

  logout(): void {
    this.authFacade.logout();
  }
}
