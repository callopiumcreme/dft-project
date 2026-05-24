'use client';

import { useEffect } from 'react';
import { useFormState, useFormStatus } from 'react-dom';
import { loginAction, type LoginState } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const initialState: LoginState = {};

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button
      type="submit"
      variant="primary"
      size="lg"
      disabled={pending}
      className="w-full"
    >
      {pending ? 'Verifying…' : 'Sign in'}
    </Button>
  );
}

export function LoginForm({ next }: { next: string }) {
  const [state, action] = useFormState(loginAction, initialState);

  useEffect(() => {
    if (!state.error) return;
    // Map error string → reason. Server already set a cookie too;
    // fire client-side here so failure on same-page rerender is captured.
    const reason =
      state.error === 'Invalid credentials'
        ? 'invalid_credentials'
        : state.error === 'Email and password required'
          ? 'missing_fields'
          : 'server_error';
    window.umami?.track('auth_login_fail', { reason });
  }, [state.error]);

  return (
    <form action={action} className="space-y-8" noValidate>
      <input type="hidden" name="next" value={next} />
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          autoFocus
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />
      </div>
      {state.error && (
        <p
          role="alert"
          className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-accent"
        >
          {state.error}
        </p>
      )}
      <SubmitButton />
    </form>
  );
}
