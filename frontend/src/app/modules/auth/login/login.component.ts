import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthFacade } from '../../core/facades/auth.facade';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
})
export class LoginComponent implements OnInit {
  form!: FormGroup;
  loading = false;
  error: string | null = null;

  constructor(
    private fb: FormBuilder,
    private authFacade: AuthFacade,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });

    this.authFacade.authState$.subscribe((state) => {
      this.loading = state.loading;
      this.error = state.error;
      if (state.isAuthenticated) {
        this.router.navigate(['/dashboard']);
      }
    });
  }

  onSubmit(): void {
    if (this.form.valid) {
      const { email, password } = this.form.value;
      this.authFacade.login(email, password);
    }
  }
}
