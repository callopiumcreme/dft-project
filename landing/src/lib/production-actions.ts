'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { apiPost, apiPatch, apiDelete, ApiError } from './api';
import type { components } from './backend-types';

type CreateBody = components['schemas']['DailyProductionCreate'];
type UpdateBody = components['schemas']['DailyProductionUpdate'];

export type ProductionFormState = {
  error?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

const TEXT_FIELDS = ['prod_date', 'contract_ref', 'pos_number', 'notes'] as const;

const NUM_FIELDS = [
  'kg_to_production',
  'eu_prod_kg',
  'plus_prod_kg',
  'carbon_black_kg',
  'metal_scrap_kg',
  'h2o_kg',
  'gas_syngas_kg',
  'losses_kg',
  'output_eu_kg',
] as const;

function pickValues(fd: FormData): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of [...TEXT_FIELDS, ...NUM_FIELDS]) {
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
  if (n < 0) {
    errs[field] = 'Must be ≥ 0';
    return null;
  }
  return trimmed;
}

type ParsedBody = {
  prod_date: string;
  kg_to_production: string | null;
  eu_prod_kg: string | null;
  plus_prod_kg: string | null;
  carbon_black_kg: string | null;
  metal_scrap_kg: string | null;
  h2o_kg: string | null;
  gas_syngas_kg: string | null;
  losses_kg: string | null;
  output_eu_kg: string | null;
  contract_ref: string | null;
  pos_number: string | null;
  notes: string | null;
};

function parseAndValidate(
  fd: FormData,
):
  | { ok: true; body: ParsedBody; values: Record<string, string> }
  | { ok: false; state: ProductionFormState } {
  const values = pickValues(fd);
  const errs: Record<string, string> = {};

  const prod_date = values.prod_date.trim();
  if (!prod_date) errs.prod_date = 'Required';
  else if (!/^\d{4}-\d{2}-\d{2}$/.test(prod_date)) errs.prod_date = 'Invalid date';
  else {
    const today = new Date().toISOString().slice(0, 10);
    if (prod_date > today) errs.prod_date = 'Cannot be future';
  }

  const parsed: Record<string, string | null> = {};
  for (const f of NUM_FIELDS) {
    parsed[f] = parseOptionalNumber(values[f], f, errs);
  }

  if (Object.keys(errs).length > 0) {
    return { ok: false, state: { fieldErrors: errs, values } };
  }

  const body: ParsedBody = {
    prod_date,
    kg_to_production: parsed.kg_to_production,
    eu_prod_kg: parsed.eu_prod_kg,
    plus_prod_kg: parsed.plus_prod_kg,
    carbon_black_kg: parsed.carbon_black_kg,
    metal_scrap_kg: parsed.metal_scrap_kg,
    h2o_kg: parsed.h2o_kg,
    gas_syngas_kg: parsed.gas_syngas_kg,
    losses_kg: parsed.losses_kg,
    output_eu_kg: parsed.output_eu_kg,
    contract_ref: values.contract_ref.trim() || null,
    pos_number: values.pos_number.trim() || null,
    notes: values.notes.trim() || null,
  };
  return { ok: true, body, values };
}

export async function createProductionAction(
  _prev: ProductionFormState,
  fd: FormData,
): Promise<ProductionFormState> {
  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  try {
    await apiPost('/daily-production', parsed.body satisfies CreateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/production');
  redirect('/app/production?created=1');
}

export async function updateProductionAction(
  id: number,
  _prev: ProductionFormState,
  fd: FormData,
): Promise<ProductionFormState> {
  const parsed = parseAndValidate(fd);
  if (!parsed.ok) return parsed.state;

  const { prod_date: _omit, ...patch } = parsed.body;
  try {
    await apiPatch(`/daily-production/${id}`, patch satisfies UpdateBody);
  } catch (e) {
    if (e instanceof ApiError) return { error: `${e.status} · ${e.detail}`, values: parsed.values };
    return { error: 'Server connection error', values: parsed.values };
  }

  revalidatePath('/app/production');
  revalidatePath(`/app/production/${id}`);
  redirect(`/app/production/${id}?updated=1`);
}

export async function deleteProductionAction(fd: FormData): Promise<void> {
  const idRaw = fd.get('id');
  const id = typeof idRaw === 'string' ? Number.parseInt(idRaw, 10) : NaN;
  if (!Number.isInteger(id) || id <= 0) {
    redirect('/app/production?error=invalid_id');
  }

  try {
    await apiDelete(`/daily-production/${id}`);
  } catch (e) {
    const detail = e instanceof ApiError ? `${e.status}_${e.detail}` : 'connection_error';
    redirect(`/app/production/${id}?error=${encodeURIComponent(detail)}`);
  }

  revalidatePath('/app/production');
  redirect('/app/production?deleted=1');
}
