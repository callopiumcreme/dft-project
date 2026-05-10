'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, ApiError } from './api';
import type { components } from './backend-types';

type Body = components['schemas']['DailyInputCreate'];

export type CreateInputState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

const TEXT_FIELDS = [
  'entry_date',
  'entry_time',
  'ersv_number',
  'c14_analysis',
  'notes',
] as const;

const NUM_FIELDS_REQUIRED_DEFAULT_ZERO = ['car_kg', 'truck_kg', 'special_kg'] as const;
const NUM_FIELDS_OPTIONAL = [
  'theor_veg_pct',
  'manuf_veg_pct',
  'c14_value',
] as const;

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

export async function createInputAction(
  _prev: CreateInputState,
  fd: FormData,
): Promise<CreateInputState> {
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
    return { fieldErrors: errs, values };
  }

  const entry_time = values.entry_time.trim() || null;
  const ersv_number = values.ersv_number.trim() || null;
  const c14_analysis = values.c14_analysis.trim() || null;
  const notes = values.notes.trim() || null;

  const body: Body = {
    entry_date,
    entry_time,
    supplier_id,
    certificate_id,
    contract_id,
    ersv_number,
    car_kg,
    truck_kg,
    special_kg,
    theor_veg_pct,
    manuf_veg_pct,
    c14_analysis,
    c14_value,
    notes,
  };

  try {
    await apiPost('/daily-inputs', body);
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: `${e.status} · ${e.detail}`, values };
    }
    return { error: 'Server connection error', values };
  }

  revalidatePath('/app/inputs');
  redirect('/app/inputs?created=1');
}
