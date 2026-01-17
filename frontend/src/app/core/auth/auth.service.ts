import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { tap, catchError, map } from 'rxjs/operators';
import { APIService } from '../api/api.service';
import { User } from '../models';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private tokenKey = 'auth_token';
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  private isAuthenticatedSubject = new BehaviorSubject<boolean>(
    this.hasToken()
  );
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  constructor(private api: APIService, private http: HttpClient) {
    this.initializeAuth();
  }

  private initializeAuth(): void {
    if (this.hasToken()) {
      this.api.getCurrentUser().subscribe({
        next: (user) => {
          this.currentUserSubject.next(user);
          this.isAuthenticatedSubject.next(true);
        },
        error: () => {
          this.logout();
        },
      });
    }
  }

  login(email: string, password: string): Observable<User> {
    return this.api.login(email, password).pipe(
      tap((response) => {
        this.setToken(response.access_token);
      }),
      switchMap(() => this.api.getCurrentUser()),
      tap((user) => {
        this.currentUserSubject.next(user);
        this.isAuthenticatedSubject.next(true);
      }),
      catchError((err) => {
        this.logout();
        return throwError(() => err);
      })
    );
  }

  logout(): void {
    this.removeToken();
    this.currentUserSubject.next(null);
    this.isAuthenticatedSubject.next(false);
  }

  private setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
  }

  private removeToken(): void {
    localStorage.removeItem(this.tokenKey);
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  hasToken(): boolean {
    return !!this.getToken();
  }

  private handleError(error: HttpErrorResponse) {
    let errorMessage = 'An error occurred';
    if (error.error instanceof ErrorEvent) {
      errorMessage = `Error: ${error.error.message}`;
    } else {
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
    }
    return throwError(() => new Error(errorMessage));
  }
}

import { switchMap } from 'rxjs/operators';
