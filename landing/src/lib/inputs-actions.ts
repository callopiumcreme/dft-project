'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, apiPatch, apiDelete, ApiError } from './api';
import type { components } from './backend-types';

type CreateBody = components['schemas']['DailyInputCreate'];
type UpdateBody = components['schemas']['DailyInputUpdate'];

export type InputFormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

// kept for backward-compat with existing imports
export type CreateInputState = InputFormState;

const TEXT_FIELDS = [
  'entry_date',
  'entry_time',
  'ersv_number',
  'c14_analysis',
  'notes',
] as const;

const NUM_FIELDS_REQUIRED_DEFAULT_ZERO = ['car_kg', 'truck_kg', 'special_kg'] as const;
const NUM_FIELDS_OPTIONAL = ['theor_veg_pct', 'manuf_veg_pct', 'c14_value'] as const;

function pickValues(fd: FormData): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of [
    ...TEXT_FIELDS,
    ...NUM_FIELDS_REQUIRED_DEFAULT_ZERO,
    ...NUM_FIELDS_OPTIONAL,
    'supplier_id',
    'certificate_id',
    'contract_id',
  ]) {
    const v = fd.get(k);
    out[k] = typeof v === 'string' ? v : '';
  }
  return out;
}

function parseOptionalNumber(
  raw: string,
  field: string,
  errs: Record<string, string>,
): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isFinite(n)) {
    errs[field] = 'Invalid number';
    return null;
  }
  if (field.endsWith('_kg') && n < 0) {
    errs[field] = 'Must be ≥ 0';
    return null;
  }
  if (field.endsWith('_pct') && (n < 0 || n > 100)) {
    errs[field] = 'Must be 0–100';
    return null;
  }
  return trimmed;
}

function parseRequiredId(
  raw: string,
  field: string,
  errs: Record<string, string>,
): number | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    errs[field] = 'Required';
    return null;
  }
  const n = Number.parseInt(trimmed, 10);
  if (!Number.isInteger(n) || n <= 0) {
    errs[field] = 'Invalid';
    return null;
  }
  return n;
}

function parseOptionalId(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const n = Number.parseInt(trimmed, 10);
  return Number.isInteger(n) && n > 0 ? n : null;
}

type ParsedBody = {
  entry_date: string;
  entry_time: string | null;
  supplier_id: number;
  certificate_id: number | null;
  contract_id: number | null;
  ersv_number: string | null;
  car_kg: string;
  truck_kg: string;
  special_kg: string;
  theor_veg_pct: string | null;
  manuf_veg_pct: string | null;
  c14_analysis: string | null;
  c14_value: string | null;
  notes: string | null;
};

function parseAndValidate(
  fd: FormData,
): { ok: true; body: ParsedBody; values: Record<string, string> } | { ok: false; state: InputFormState } {
  const values = pickValues(fd);
  const errs: Record<string, string> = {};

  const entry_date = values.entry_date.trim();
  if (!entry_date) errs.entry_date = 'Required';
  else if (!/^\d{4}-\d{2}-\d{2}$/.test(entry_date)) errs.entry_date = 'Invalid date';
  else {
    const today = new Date().toISOString().slice(0, 10);
    if (entry_date > today) errs.entry_date = 'Cannot be future';
  }

  const supplier_id = parseRequiredId(values.supplier_id, 'supplier_id', errs);
  const certificate_id = parseOptionalId(values.certificate_id);
  const contract_id = parseOptionalId(values.contract_id);

  const car_kg = parseOptionalNumber(values.car_kg, 'car_kg', errs) ?? '0';
  const truck_kg = parseOptionalNumber(values.truck_kg, 'truck_kg', errs) ?? '0';
  const special_kg = parseOptionalNumber(values.special_kg, 'special_kg', errs) ?? '0';

  const theor_veg_pct = parseOptionalNumber(values.theor_veg_pct, 'theor_veg_pct', errs);
  const manuf_veg_pct = parseOptionalNumber(values.manuf_veg_pct, 'manuf_veg_pct', errs);
  const c14_value = parseOptionalNumber(values.c14_value, 'c14_value', errs);

  const totalInput = Number(car_kg) + Number(truck_kg) + Number(special_kg);
  if (totalInput <= 0) {
    errs.car_kg = errs.car_kg || 'At least one weight > 0';
  }

  if (Object.keys(errs).length > 0 || supplier_id === null) {
    return { ok: false, state: { fieldErrors: errs, values } };
  }

  const body: ParsedBody = {
    entry_date,
    entry_time: values.entry_time.trim() || null,
    supplier_id,
    certificate_id,
    contract_id,
    ersv_number: values.ersv_number.trim() || null,
    car_kg,
    truck_kg,
    special_kg,
    theor_veg_pct,
    manuf_veg_pct,
    c14_analysis: values.c14_analysis.trim() || null,
    c14_value,
    notes: values.notes.trim() || null,
  };
  return { ok: true, body, values };
}

export async function createInputAction(
  _prev: InputFormState,
  fd: FormData,
): Promise<InputFormState> {
  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPost('/daily-inputs', parsed.body satisfies CreateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/inputs');
  redirect('/app/inputs?created=1');
}

export async function updateInputAction(
  id: number,
  _prev: InputFormState,
  fd: FormData,
): Promise<InputFormState> {
  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPatch(`/daily-inputs/${id}`, parsed.body satisfies UpdateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/inputs');
  revalidatePath(`/app/inputs/${id}`);
  redirect(`/app/inputs/${id}?updated=1`);
}

export async function deleteInputAction(fd: FormData): Promise<void> {
  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/inputs?error=invalid_id');
  }

  try {
    await apiDelete(`/daily-inputs/${id}`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/inputs/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/inputs');
  redirect('/app/inputs?deleted=1');
}
