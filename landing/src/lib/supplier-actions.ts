'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, apiPatch, apiDelete, apiGet, ApiError } from './api';
import type { components } from './backend-types';

type CreateBody = components['schemas']['SupplierCreate'];
type UpdateBody = components['schemas']['SupplierUpdate'];
type UserRead = components['schemas']['UserRead'];

export type SupplierFormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

const CODE_RE = /^[A-Za-z0-9._-]{1,32}$/;

async function ensureAdmin(): Promise<{ ok: true } | { ok: false; state: SupplierFormState }> {
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
  for (const k of ['name', 'code', 'country', 'active', 'is_aggregate', 'notes']) {
    const v = fd.get(k);
    out[k] = typeof v === 'string' ? v : '';
  }
  return out;
}

type ParsedBody = {
  name: string;
  code: string;
  country: string | null;
  active: boolean;
  is_aggregate: boolean;
  notes: string | null;
};

function parseAndValidate(
  fd: FormData,
): { ok: true; body: ParsedBody; values: Record<string, string> } | { ok: false; state: SupplierFormState } {
  const values = pickValues(fd);
  const errs: Record<string, string> = {};

  const name = values.name.trim();
  if (!name) errs.name = 'Required';
  else if (name.length > 200) errs.name = 'Max 200 chars';

  const code = values.code.trim();
  if (!code) errs.code = 'Required';
  else if (!CODE_RE.test(code)) errs.code = 'Letters, digits, . _ - (max 32)';

  const country = values.country.trim();
  if (country && country.length > 80) errs.country = 'Max 80 chars';

  const notes = values.notes;
  if (notes.length > 4000) errs.notes = 'Max 4000 chars';

  if (Object.keys(errs).length > 0) {
    return { ok: false, state: { fieldErrors: errs, values } };
  }

  return {
    ok: true,
    body: {
      name,
      code,
      country: country || null,
      active: values.active === 'on' || values.active === 'true' || values.active === '1',
      is_aggregate:
        values.is_aggregate === 'on' || values.is_aggregate === 'true' || values.is_aggregate === '1',
      notes: notes.trim() || null,
    },
    values,
  };
}

export async function createSupplierAction(
  _prev: SupplierFormState,
  fd: FormData,
): Promise<SupplierFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  let createdId: number;
  try {
    const created = await apiPost<components['schemas']['SupplierRead']>(
      '/suppliers',
      parsed.body satisfies CreateBody,
    );
    createdId = created.id;
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/suppliers');
  redirect(`/app/suppliers/${createdId}?created=1`);
}

export async function updateSupplierAction(
  id: number,
  _prev: SupplierFormState,
  fd: FormData,
): Promise<SupplierFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPatch(`/suppliers/${id}`, parsed.body satisfies UpdateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/suppliers');
  revalidatePath(`/app/suppliers/${id}`);
  redirect(`/app/suppliers/${id}?updated=1`);
}

export async function deleteSupplierAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/suppliers?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/suppliers?error=invalid_id');
  }

  try {
    await apiDelete(`/suppliers/${id}`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/suppliers/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/suppliers');
  redirect('/app/suppliers?deleted=1');
}

export async function restoreSupplierAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/suppliers?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/suppliers?error=invalid_id');
  }

  try {
    await apiPost(`/suppliers/${id}/restore`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/suppliers/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/suppliers');
  redirect(`/app/suppliers/${id}?restored=1`);
}
