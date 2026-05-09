'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { apiPost, ApiError, SESSION_COOKIE } from './api';
import type { components } from './backend-types';

type LoginRequest = components['schemas']['LoginRequest'];
type TokenResponse = components['schemas']['TokenResponse'];

export type LoginState = { error?: string };

const COOKIE_MAX_AGE = 60 * 60 * 8;

function safeNext(raw: unknown): string {
  if (typeof raw !== 'string') return '/app';
  if (!raw.startsWith('/')) return '/app';
  if (raw.startsWith('//') || raw.startsWith('/\\')) return '/app';
  if (raw === '/login') return '/app';
  return raw;
}

export async function loginAction(_prev: LoginState, fd: FormData): Promise<LoginState> {
  const email = String(fd.get('email') ?? '').trim();
  const password = String(fd.get('password') ?? '');
  const next = safeNext(fd.get('next'));

  if (!email || !password) {
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
      return { error: 'Invalid credentials' };
    }
    return { error: 'Server connection error' };
  }

  cookies().set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: COOKIE_MAX_AGE,
  });

  redirect(next);
}

export async function logoutAction(): Promise<void> {
  cookies().delete(SESSION_COOKIE);
  redirect('/');
}
