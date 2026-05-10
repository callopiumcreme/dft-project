'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, apiPatch, apiDelete, apiGet, ApiError } from './api';
import type { components } from './backend-types';

type CreateBody = components['schemas']['UserCreate'];
type UpdateBody = components['schemas']['UserUpdate'];
type UserRead = components['schemas']['UserRead'];

type Role = 'admin' | 'operator' | 'viewer' | 'certifier';
const ROLES: Role[] = ['admin', 'operator', 'viewer', 'certifier'];

export type UserFormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const FORBIDDEN_TLDS = new Set(['.test', '.example', '.local', '.invalid']);

async function ensureAdmin(): Promise<{ ok: true } | { ok: false; state: UserFormState }> {
  try {
    const me = await apiGet<UserRead>('/auth/me');
    if (me.role !== 'admin') {
      return { ok: false, state: { error: 'Admin role required' } };
    }
    return { ok: true };
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    return { ok: false, state: { error: 'Server connection error' } };
  }
}

function pickValues(fd: FormData): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of ['email', 'full_name', 'role', 'active', 'password']) {
    const v = fd.get(k);
    out[k] = typeof v === 'string' ? v : '';
  }
  return out;
}

type ParsedCreate = {
  email: string;
  full_name: string | null;
  role: Role;
  active: boolean;
  password: string;
};

type ParsedUpdate = {
  full_name: string | null;
  role: Role | null;
  active: boolean | null;
  password: string | null;
};

function validateCommon(values: Record<string, string>): {
  errs: Record<string, string>;
  full_name: string | null;
  roleVal: Role | null;
  active: boolean;
} {
  const errs: Record<string, string> = {};
  const full_name = values.full_name.trim() || null;
  const roleRaw = values.role.trim();
  const roleVal = (ROLES as readonly string[]).includes(roleRaw) ? (roleRaw as Role) : null;
  if (!roleVal) errs.role = 'Required';
  const active =
    values.active === 'on' || values.active === 'true' || values.active === '1';
  return { errs, full_name, roleVal, active };
}

function parseCreate(
  fd: FormData,
):
  | { ok: true; body: ParsedCreate; values: Record<string, string> }
  | { ok: false; state: UserFormState } {
  const values = pickValues(fd);
  const { errs, full_name, roleVal, active } = validateCommon(values);

  const email = values.email.trim().toLowerCase();
  if (!email) errs.email = 'Required';
  else if (!EMAIL_RE.test(email)) errs.email = 'Invalid email';
  else {
    for (const tld of FORBIDDEN_TLDS) {
      if (email.endsWith(tld)) {
        errs.email = `${tld} TLD not allowed`;
        break;
      }
    }
  }

  const password = values.password;
  if (!password) errs.password = 'Required';
  else if (password.length < 8) errs.password = 'At least 8 characters';
  else if (Buffer.byteLength(password, 'utf8') > 72) errs.password = 'Max 72 bytes';

  if (Object.keys(errs).length > 0) {
    return { ok: false, state: { fieldErrors: errs, values } };
  }

  return {
    ok: true,
    body: {
      email,
      full_name,
      role: roleVal as Role,
      active,
      password,
    },
    values,
  };
}

function parseUpdate(
  fd: FormData,
):
  | { ok: true; body: ParsedUpdate; values: Record<string, string> }
  | { ok: false; state: UserFormState } {
  const values = pickValues(fd);
  const { errs, full_name, roleVal, active } = validateCommon(values);

  const password = values.password;
  let pwOut: string | null = null;
  if (password) {
    if (password.length < 8) errs.password = 'At least 8 characters';
    else if (Buffer.byteLength(password, 'utf8') > 72) errs.password = 'Max 72 bytes';
    else pwOut = password;
  }

  if (Object.keys(errs).length > 0) {
    return { ok: false, state: { fieldErrors: errs, values } };
  }

  return {
    ok: true,
    body: {
      full_name,
      role: roleVal,
      active,
      password: pwOut,
    },
    values,
  };
}

export async function createUserAction(
  _prev: UserFormState,
  fd: FormData,
): Promise<UserFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseCreate(fd);
  if (!parsed.ok) return parsed.state;

  let createdId: number;
  try {
    const created = await apiPost<UserRead>('/users', parsed.body satisfies CreateBody);
    createdId = created.id;
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/users');
  redirect(`/app/users/${createdId}?created=1`);
}

export async function updateUserAction(
  id: number,
  _prev: UserFormState,
  fd: FormData,
): Promise<UserFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseUpdate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPatch(`/users/${id}`, parsed.body satisfies UpdateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/users');
  revalidatePath(`/app/users/${id}`);
  redirect(`/app/users/${id}?updated=1`);
}

export async function deactivateUserAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/users?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/users?error=invalid_id');
  }

  try {
    await apiDelete(`/users/${id}`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/users/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/users');
  redirect('/app/users?deactivated=1');
}

export async function reactivateUserAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/users?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/users?error=invalid_id');
  }

  try {
    await apiPost(`/users/${id}/restore`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/users/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/users');
  redirect(`/app/users/${id}?reactivated=1`);
}
