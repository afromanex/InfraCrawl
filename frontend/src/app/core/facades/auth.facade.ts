import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { User } from '../models';
import { AuthService } from '../auth/auth.service';

@Injectable({
  providedIn: 'root',
})
export class AuthFacade {
  private authStateSubject = new BehaviorSubject<{
    isAuthenticated: boolean;
    currentUser: User | null;
    loading: boolean;
    error: string | null;
  }>({
    isAuthenticated: false,
    currentUser: null,
    loading: false,
    error: null,
  });

  authState$ = this.authStateSubject.asObservable();
  isAuthenticated$;
  currentUser$;

  constructor(private authService: AuthService, private router: Router) {
    this.isAuthenticated$ = this.authService.isAuthenticated$;
    this.currentUser$ = this.authService.currentUser$;
    this.authService.isAuthenticated$.subscribe((isAuth: boolean) => {
      const state = this.authStateSubject.value;
      this.authStateSubject.next({ ...state, isAuthenticated: isAuth });
    });

    this.authService.currentUser$.subscribe((user: User | null) => {
      const state = this.authStateSubject.value;
      this.authStateSubject.next({ ...state, currentUser: user });
    });
  }

  login(password: string): void {
    const state = this.authStateSubject.value;
    this.authStateSubject.next({
      ...state,
      loading: true,
      error: null,
    });

    this.authService.login(password).subscribe({
      next: () => {
        const newState = this.authStateSubject.value;
        this.authStateSubject.next({
          ...newState,
          isAuthenticated: true,
          loading: false,
          error: null,
        });
      },
      error: (err: any) => {
        const newState = this.authStateSubject.value;
        this.authStateSubject.next({
          ...newState,
          isAuthenticated: false,
          loading: false,
          error: err?.error?.detail || 'Login failed',
        });
      },
    });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
