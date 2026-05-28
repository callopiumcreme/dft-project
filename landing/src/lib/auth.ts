'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { apiPost, ApiError, SESSION_COOKIE } from './api';
import type { components } from './backend-types';
import { welcomePathFor } from '@/config/welcome-routing';

type LoginRequest = components['schemas']['LoginRequest'];
type TokenResponse = components['schemas']['TokenResponse'];

export type LoginState = { error?: string };

const COOKIE_MAX_AGE = 60 * 60 * 8;

const PENDING_UMAMI_COOKIE = '__umami_pending';

function setPendingUmamiEvent(name: string, data: Record<string, unknown> = {}): void {
  cookies().set(PENDING_UMAMI_COOKIE, JSON.stringify({ name, data }), {
    httpOnly: false, // client must read it
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 60, // short-lived; consumed on next page load
  });
}

function safeNext(raw: unknown): string {
  if (typeof raw !== 'string') return '/app';
  if (!raw.startsWith('/')) return '/app';
  if (raw.startsWith('//') || raw.startsWith('/\\')) return '/app';
  if (raw === '/login') return '/app';
  return raw;
}

export async function loginAction(_prev: LoginState, fd: FormData): Promise<LoginState> {
  const email = String(fd.get('email') ?? '').trim().toLowerCase();
  const password = String(fd.get('password') ?? '');
  const next = safeNext(fd.get('next'));

  if (!email || !password) {
    setPendingUmamiEvent('auth_login_fail', { reason: 'missing_fields' });
    return { error: 'Email and password required' };
  }

  let token: string;
  try {
    const res = await apiPost<TokenResponse>(
      '/auth/login',
      { email, password } satisfies LoginRequest,
      { noAuth: true },
    );
    token = res.access_token;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      setPendingUmamiEvent('auth_login_fail', { reason: 'invalid_credentials' });
      return { error: 'Invalid credentials' };
    }
    setPendingUmamiEvent('auth_login_fail', { reason: 'server_error' });
    return { error: 'Server connection error' };
  }

  cookies().set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: COOKIE_MAX_AGE,
  });

  setPendingUmamiEvent('auth_login_success', {});

  // Per-user welcome route: when the user has no explicit `next` (i.e. they
  // landed on /login directly and would default to /app), send them to their
  // welcome page instead. An explicit `next` (e.g. from middleware after a
  // deep link) is always honored.
  const welcome = welcomePathFor(email);
  redirect(welcome && next === '/app' ? welcome : next);
}

export async function logoutAction(): Promise<void> {
  setPendingUmamiEvent('auth_logout', {});
  cookies().delete(SESSION_COOKIE);
  redirect('/');
}
