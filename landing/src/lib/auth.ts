'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { apiPost, ApiError, SESSION_COOKIE } from './api';
import type { components } from './backend-types';

type LoginRequest = components['schemas']['LoginRequest'];
type TokenResponse = components['schemas']['TokenResponse'];

export type LoginState = { error?: string };

const COOKIE_MAX_AGE = 60 * 60 * 8;

export async function loginAction(_prev: LoginState, fd: FormData): Promise<LoginState> {
  const email = String(fd.get('email') ?? '').trim();
  const password = String(fd.get('password') ?? '');

  if (!email || !password) {
    return { error: 'Email e password obbligatori' };
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
      return { error: 'Credenziali non valide' };
    }
    return { error: 'Errore di connessione al server' };
  }

  cookies().set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: COOKIE_MAX_AGE,
  });

  redirect('/app');
}

export async function logoutAction(): Promise<void> {
  cookies().delete(SESSION_COOKIE);
  redirect('/');
}
