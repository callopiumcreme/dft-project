import 'server-only';
import { cookies } from 'next/headers';
import type { paths } from './backend-types';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:18000';
export const SESSION_COOKIE = 'dft_session';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly payload?: unknown,
  ) {
    super(`API ${status}: ${detail}`);
    this.name = 'ApiError';
  }
}

type QueryValue = string | number | boolean | null | undefined;

export interface ApiOptions {
  query?: Record<string, QueryValue | QueryValue[]>;
  signal?: AbortSignal;
  noAuth?: boolean;
  token?: string;
  cache?: RequestCache;
}

function buildUrl(path: string, query?: ApiOptions['query']): string {
  const url = new URL(path.startsWith('/') ? path : `/${path}`, BACKEND_URL);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null) continue;
      if (Array.isArray(v)) {
        for (const item of v) {
          if (item !== undefined && item !== null) url.searchParams.append(k, String(item));
        }
      } else {
        url.searchParams.set(k, String(v));
      }
    }
  }
  return url.toString();
}

function resolveToken(opts: ApiOptions): string | undefined {
  if (opts.noAuth) return undefined;
  if (opts.token) return opts.token;
  try {
    return cookies().get(SESSION_COOKIE)?.value;
  } catch {
    return undefined;
  }
}

async function request<T>(
  method: string,
  path: string,
  body: unknown,
  opts: ApiOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const token = resolveToken(opts);
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(buildUrl(path, opts.query), {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: opts.signal,
    cache: opts.cache ?? 'no-store',
  });

  if (!res.ok) {
    let payload: unknown;
    try {
      payload = await res.json();
    } catch {
      // ignore
    }
    const detail =
      payload && typeof payload === 'object' && 'detail' in payload
        ? String((payload as { detail: unknown }).detail)
        : res.statusText || 'Request failed';
    throw new ApiError(res.status, detail, payload);
  }

  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

export function apiGet<T>(path: string, opts?: ApiOptions): Promise<T> {
  return request<T>('GET', path, undefined, opts);
}

export function apiPost<T>(path: string, body?: unknown, opts?: ApiOptions): Promise<T> {
  return request<T>('POST', path, body, opts);
}

export function apiPatch<T>(path: string, body?: unknown, opts?: ApiOptions): Promise<T> {
  return request<T>('PATCH', path, body, opts);
}

export function apiDelete<T>(path: string, opts?: ApiOptions): Promise<T> {
  return request<T>('DELETE', path, undefined, opts);
}

export type Paths = paths;

export type GetResponse<P extends keyof paths> = paths[P] extends {
  get: { responses: { 200: { content: { 'application/json': infer R } } } };
}
  ? R
  : never;

export type PostResponse<P extends keyof paths> = paths[P] extends {
  post: { responses: { 200: { content: { 'application/json': infer R } } } };
}
  ? R
  : paths[P] extends {
        post: { responses: { 201: { content: { 'application/json': infer R } } } };
      }
    ? R
    : never;

export type PostBody<P extends keyof paths> = paths[P] extends {
  post: { requestBody: { content: { 'application/json': infer B } } };
}
  ? B
  : never;
