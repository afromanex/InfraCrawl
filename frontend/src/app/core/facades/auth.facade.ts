import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
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
  isAuthenticated$ = this.authService.isAuthenticated$;
  currentUser$ = this.authService.currentUser$;

  constructor(private authService: AuthService) {
    this.authService.isAuthenticated$.subscribe((isAuth) => {
      const state = this.authStateSubject.value;
      this.authStateSubject.next({ ...state, isAuthenticated: isAuth });
    });

    this.authService.currentUser$.subscribe((user) => {
      const state = this.authStateSubject.value;
      this.authStateSubject.next({ ...state, currentUser: user });
    });
  }

  login(email: string, password: string): void {
    const state = this.authStateSubject.value;
    this.authStateSubject.next({ ...state, loading: true, error: null });

    this.authService.login(email, password).subscribe({
      next: () => {
        const newState = this.authStateSubject.value;
        this.authStateSubject.next({ ...newState, loading: false });
      },
      error: (err) => {
        const newState = this.authStateSubject.value;
        this.authStateSubject.next({
          ...newState,
          loading: false,
          error: err.message || 'Login failed',
        });
      },
    });
  }

  logout(): void {
    this.authService.logout();
  }
}
