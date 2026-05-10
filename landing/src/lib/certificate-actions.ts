'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, apiPatch, apiDelete, apiGet, ApiError } from './api';
import type { components } from './backend-types';

type CreateBody = components['schemas']['CertificateCreate'];
type UpdateBody = components['schemas']['CertificateUpdate'];
type UserRead = components['schemas']['UserRead'];

export type CertificateFormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
  supplierIds?: number[];
};

const NUMBER_RE = /^[A-Za-z0-9._\-/ ]{1,64}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const STATUSES = ['active', 'expired', 'revoked', 'placeholder'] as const;
type Status = (typeof STATUSES)[number];

async function ensureAdmin(): Promise<{ ok: true } | { ok: false; state: CertificateFormState }> {
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
    'cert_number',
    'scheme',
    'status',
    'issued_at',
    'expires_at',
    'is_placeholder',
    'document_url',
    'notes',
  ]) {
    const v = fd.get(k);
    out[k] = typeof v === 'string' ? v : '';
  }
  return out;
}

function pickSupplierIds(fd: FormData): number[] {
  const all = fd.getAll('supplier_ids');
  const out: number[] = [];
  for (const v of all) {
    if (typeof v !== 'string') continue;
    const n = Number.parseInt(v, 10);
    if (Number.isInteger(n) && n > 0 && !out.includes(n)) out.push(n);
  }
  return out;
}

type ParsedBody = {
  cert_number: string;
  scheme: string;
  status: Status;
  issued_at: string | null;
  expires_at: string | null;
  is_placeholder: boolean;
  document_url: string | null;
  notes: string | null;
  supplier_ids: number[];
};

function parseAndValidate(
  fd: FormData,
):
  | { ok: true; body: ParsedBody; values: Record<string, string>; supplierIds: number[] }
  | { ok: false; state: CertificateFormState } {
  const values = pickValues(fd);
  const supplierIds = pickSupplierIds(fd);
  const errs: Record<string, string> = {};

  const cert_number = values.cert_number.trim();
  if (!cert_number) errs.cert_number = 'Required';
  else if (!NUMBER_RE.test(cert_number))
    errs.cert_number = 'Letters, digits, . _ - / space (max 64)';

  const scheme = values.scheme.trim() || 'ISCC EU';
  if (scheme.length > 64) errs.scheme = 'Max 64 chars';

  const statusRaw = values.status.trim() || 'active';
  if (!(STATUSES as readonly string[]).includes(statusRaw)) {
    errs.status = 'Invalid status';
  }
  const status = statusRaw as Status;

  const issued_at = values.issued_at.trim();
  if (issued_at && !DATE_RE.test(issued_at)) errs.issued_at = 'YYYY-MM-DD';
  const expires_at = values.expires_at.trim();
  if (expires_at && !DATE_RE.test(expires_at)) errs.expires_at = 'YYYY-MM-DD';
  if (
    !errs.issued_at &&
    !errs.expires_at &&
    issued_at &&
    expires_at &&
    expires_at < issued_at
  ) {
    errs.expires_at = 'Expires must be ≥ issued';
  }

  const document_url = values.document_url.trim();
  if (document_url && !/^https?:\/\//i.test(document_url))
    errs.document_url = 'Must start with http:// or https://';
  if (document_url.length > 1000) errs.document_url = 'Max 1000 chars';

  const notes = values.notes;
  if (notes.length > 4000) errs.notes = 'Max 4000 chars';

  if (Object.keys(errs).length > 0) {
    return { ok: false, state: { fieldErrors: errs, values, supplierIds } };
  }

  return {
    ok: true,
    body: {
      cert_number,
      scheme,
      status,
      issued_at: issued_at || null,
      expires_at: expires_at || null,
      is_placeholder:
        values.is_placeholder === 'on' ||
        values.is_placeholder === 'true' ||
        values.is_placeholder === '1',
      document_url: document_url || null,
      notes: notes.trim() || null,
      supplier_ids: supplierIds,
    },
    values,
    supplierIds,
  };
}

export async function createCertificateAction(
  _prev: CertificateFormState,
  fd: FormData,
): Promise<CertificateFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  let createdId: number;
  try {
    const created = await apiPost<components['schemas']['CertificateRead']>(
      '/certificates',
      parsed.body satisfies CreateBody,
    );
    createdId = created.id;
  } catch (e) {
    if (e instanceof ApiError)
      return {
        error: `${e.status} · ${e.detail}`,
        values: parsed.values,
        supplierIds: parsed.supplierIds,
      };
    return {
      error: 'Server connection error',
      values: parsed.values,
      supplierIds: parsed.supplierIds,
    };
  }

  revalidatePath('/app/certificates');
  redirect(`/app/certificates/${createdId}?created=1`);
}

export async function updateCertificateAction(
  id: number,
  _prev: CertificateFormState,
  fd: FormData,
): Promise<CertificateFormState> {
  const guard = await ensureAdmin();
  if (!guard.ok) return guard.state;

  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPatch(`/certificates/${id}`, parsed.body satisfies UpdateBody);
  } catch (e) {
    if (e instanceof ApiError)
      return {
        error: `${e.status} · ${e.detail}`,
        values: parsed.values,
        supplierIds: parsed.supplierIds,
      };
    return {
      error: 'Server connection error',
      values: parsed.values,
      supplierIds: parsed.supplierIds,
    };
  }

  revalidatePath('/app/certificates');
  revalidatePath(`/app/certificates/${id}`);
  redirect(`/app/certificates/${id}?updated=1`);
}

export async function deleteCertificateAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/certificates?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/certificates?error=invalid_id');
  }

  try {
    await apiDelete(`/certificates/${id}`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/certificates/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/certificates');
  redirect('/app/certificates?deleted=1');
}

export async function restoreCertificateAction(fd: FormData): Promise<void> {
  const guard = await ensureAdmin();
  if (!guard.ok) {
    redirect('/app/certificates?error=admin_required');
  }

  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/certificates?error=invalid_id');
  }

  try {
    await apiPost(`/certificates/${id}/restore`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/certificates/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/certificates');
  redirect(`/app/certificates/${id}?restored=1`);
}
