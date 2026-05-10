'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, apiPatch, apiDelete, apiGet, ApiError } from './api';
import type { components } from './backend-types';

type CreateBody = components['schemas']['ContractCreate'];
type UpdateBody = components['schemas']['ContractUpdate'];
type UserRead = components['schemas']['UserRead'];

export type ContractFormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

const CODE_RE = /^[A-Za-z0-9._\-/]{1,32}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

async function ensureAdmin(): Promise<{ ok: true } | { ok: false; state: ContractFormState }> {
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
  for (const k of [
    'code',
    'supplier_id',
    'start_date',
    'end_date',
    'total_kg_committed',
    'is_placeholder',
    'notes',
  ]) {
    const v = fd.get(k);
    out[k] = typeof v === 'string' ? v : '';
  }
  return out;
}

type ParsedBody = {
  code: string;
  supplier_id: number | null;
  start_date: string | null;
  end_date: string | null;
  total_kg_committed: string | null;
  is_placeholder: boolean;
  notes: string | null;
};

function parseAndValidate(
  fd: FormData,
):
  | { ok: true; body: ParsedBody; values: Record<string, string> }
  | { ok: false; state: ContractFormState } {
  const values = pickValues(fd);
  const errs: Record<string, string> = {};

  const code = values.code.trim();
  if (!code) errs.code = 'Required';
  else if (!CODE_RE.test(code)) errs.code = 'Letters, digits, . _ - / (max 32)';

  let supplier_id: number | null = null;
  if (values.supplier_id) {
    const n = Number.parseInt(values.supplier_id, 10);
    if (!Number.isInteger(n) || n <= 0) errs.supplier_id = 'Invalid supplier';
    else supplier_id = n;
  }

  const start_date = values.start_date.trim();
  if (start_date && !DATE_RE.test(start_date)) errs.start_date = 'YYYY-MM-DD';
  const end_date = values.end_date.trim();
  if (end_date && !DATE_RE.test(end_date)) errs.end_date = 'YYYY-MM-DD';
  if (!errs.start_date && !errs.end_date && start_date && end_date && end_date < start_date) {
    errs.end_date = 'End must be ≥ start';
  }

  const kgRaw = values.total_kg_committed.trim();
  let total_kg_committed: string | null = null;
  if (kgRaw) {
    const n = Number(kgRaw);
    if (!Number.isFinite(n) || n < 0) errs.total_kg_committed = 'Number ≥ 0';
    else total_kg_committed = n.toFixed(3);
  }

  const notes = values.notes;
  if (notes.length > 4000) errs.notes = 'Max 4000 chars';

  if (Object.keys(errs).length > 0) {
    return { ok: false, state: { fieldErrors: errs, values } };
  }

  return {
    ok: true,
    body: {
      code,
      supplier_id,
      start_date: start_date || null,
      end_date: end_date || null,
      total_kg_committed,
      is_placeholder:
        values.is_placeholder === 'on' ||
        values.is_placeholder === 'true' ||
        values.is_placeholder === '1',
      notes: notes.trim() || null,
    },
    values,
  };
}

export async function createContractAction(
  _prev: ContractFormState,
  fd: FormData,
): Promise<ContractFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  let createdId: number;
  try {
    const created = await apiPost<components['schemas']['ContractRead']>(
      '/contracts',
      parsed.body satisfies CreateBody,
    );
    createdId = created.id;
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/contracts');
  redirect(`/app/contracts/${createdId}?created=1`);
}

export async function updateContractAction(
  id: number,
  _prev: ContractFormState,
  fd: FormData,
): Promise<ContractFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPatch(`/contracts/${id}`, parsed.body satisfies UpdateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/contracts');
  revalidatePath(`/app/contracts/${id}`);
  redirect(`/app/contracts/${id}?updated=1`);
}

export async function deleteContractAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/contracts?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/contracts?error=invalid_id');
  }

  try {
    await apiDelete(`/contracts/${id}`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/contracts/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/contracts');
  redirect('/app/contracts?deleted=1');
}

export async function restoreContractAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/contracts?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/contracts?error=invalid_id');
  }

  try {
    await apiPost(`/contracts/${id}/restore`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/contracts/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/contracts');
  redirect(`/app/contracts/${id}?restored=1`);
}
