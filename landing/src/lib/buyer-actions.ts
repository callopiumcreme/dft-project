'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, apiPatch, apiDelete, apiGet, ApiError } from './api';
import type { components } from './backend-types';
import { setPendingUmamiEvent } from './umami-server';

type UserRead = components['schemas']['UserRead'];

export type BuyerFormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

interface BuyerOut {
  id: number;
  name: string;
  country: string | null;
  vat: string | null;
  contact: string | null;
  notes: string | null;
  created_at: string;
}

type CreateBody = {
  name: string;
  country: string | null;
  vat: string | null;
  contact: string | null;
  notes: string | null;
};

type UpdateBody = Partial<CreateBody>;

async function ensureRole(
  minimum: 'operator' | 'admin',
): Promise<{ ok: true; role: string } | { ok: false; state: BuyerFormState }> {
  try {
    const me = await apiGet<UserRead>('/auth/me');
    const role = me.role;
    if (minimum === 'admin' && role !== 'admin') {
      return { ok: false, state: { error: 'Admin role required' } };
    }
    if (minimum === 'operator' && role !== 'admin' && role !== 'operator') {
      return { ok: false, state: { error: 'Operator role required' } };
    }
    return { ok: true, role };
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    return { ok: false, state: { error: 'Server connection error' } };
  }
}

function pickValues(fd: FormData): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of ['name', 'country', 'vat', 'contact', 'notes']) {
    const v = fd.get(k);
    out[k] = typeof v === 'string' ? v : '';
  }
  return out;
}

function parseAndValidate(
  fd: FormData,
):
  | { ok: true; body: CreateBody; values: Record<string, string> }
  | { ok: false; state: BuyerFormState } {
  const values = pickValues(fd);
  const errs: Record<string, string> = {};

  const name = values.name.trim();
  if (!name) errs.name = 'Required';
  else if (name.length < 2) errs.name = 'Min 2 chars';
  else if (name.length > 200) errs.name = 'Max 200 chars';

  const country = values.country.trim();
  if (country.length > 80) errs.country = 'Max 80 chars';

  const vat = values.vat.trim();
  if (vat.length > 60) errs.vat = 'Max 60 chars';

  const contact = values.contact.trim();
  if (contact.length > 200) errs.contact = 'Max 200 chars';

  const notes = values.notes;
  if (notes.length > 4000) errs.notes = 'Max 4000 chars';

  if (Object.keys(errs).length > 0) {
    return { ok: false, state: { fieldErrors: errs, values } };
  }

  return {
    ok: true,
    body: {
      name,
      country: country || null,
      vat: vat || null,
      contact: contact || null,
      notes: notes.trim() || null,
    },
    values,
  };
}

export async function createBuyerAction(
  _prev: BuyerFormState,
  fd: FormData,
): Promise<BuyerFormState> {
  const guard = await ensureRole('operator');
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  let createdId: number;
  try {
    const created = await apiPost<BuyerOut>(
      '/byproduct/buyers',
      parsed.body satisfies CreateBody,
    );
    createdId = created.id;
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  setPendingUmamiEvent('buyer_created', { id: createdId });
  revalidatePath('/app/buyers');
  redirect(`/app/buyers/${createdId}?created=1`);
}

export async function updateBuyerAction(
  id: number,
  _prev: BuyerFormState,
  fd: FormData,
): Promise<BuyerFormState> {
  const guard = await ensureRole('operator');
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPatch(`/byproduct/buyers/${id}`, parsed.body satisfies UpdateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  setPendingUmamiEvent('buyer_updated', { id });
  revalidatePath('/app/buyers');
  revalidatePath(`/app/buyers/${id}`);
  redirect(`/app/buyers/${id}?updated=1`);
}

export async function deleteBuyerAction(fd: FormData): Promise<void> {
  const guard = await ensureRole('admin');
  if (!guard.ok) {
    redirect('/app/buyers?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/buyers?error=invalid_id');
  }

  try {
    await apiDelete(`/byproduct/buyers/${id}`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/buyers/${id}?error=${encodeURIComponent(detail)}`);
  }

  setPendingUmamiEvent('buyer_deleted', { id });
  revalidatePath('/app/buyers');
  redirect('/app/buyers?deleted=1');
}
