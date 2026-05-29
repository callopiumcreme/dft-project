/**
 * Byproduct sales client — used both server-side (via cookies() + apiGet)
 * and client-side (via fetch to /api/byproduct/* proxies).
 *
 * Backend routes live in app.routers.byproduct_sales (/byproduct/*).
 * Pattern mirrors contract-client.ts.
 */

// eu_oil = DEV-P100 (Crown Oil main product) — included for display/filter
// only. The byproduct_sale CHECK constraint excludes eu_oil; the backend
// projects Crown rows read-only from consignment_pos_customs (see
// CUSTOMS_VIRTUAL_OFFSET in app/routers/byproduct_sales.py). The "New sale"
// form keeps the 3 byproduct kinds only since eu_oil cannot be inserted.
export type SellableKind = 'plus_oil' | 'carbon_black' | 'metal_scrap' | 'eu_oil';

export const SELLABLE_KIND_LABELS: Record<SellableKind, string> = {
  plus_oil: 'DEV-P200',
  carbon_black: 'Carbon black',
  metal_scrap: 'Metal scrap',
  eu_oil: 'DEV-P100',
};

export interface ByproductBuyer {
  id: number;
  name: string;
  country: string | null;
  vat: string | null;
  contact: string | null;
  notes: string | null;
  created_at: string;
}

export interface ByproductBuyerIn {
  name: string;
  country?: string;
  vat?: string;
  contact?: string;
  notes?: string;
}

export type ByproductBuyerPatch = Partial<ByproductBuyerIn>;

export interface ByproductSale {
  id: number;
  product_kind: SellableKind;
  buyer_id: number;
  buyer_name: string | null;
  sale_date: string;
  kg_net: string;
  invoice_no: string | null;
  price_eur: string | null;
  // Multi-currency extension (Conquer Trade DEV-P200 sales priced in USD).
  // price_eur is kept for backwards compatibility; price_amount + currency
  // are the source of truth going forward.
  price_amount: string | null;
  currency: string | null;
  pricing_method: string | null;
  has_pdf: boolean;
  // POS pairing — populated only for virtual Crown DEV-P100 rows (paired
  // with consignment_pos via the same consignment_id + pos_number). For
  // Conquer-style byproduct_sale rows pos_no is null and has_pos_pdf is false.
  pos_no: string | null;
  has_pos_pdf: boolean;
  notes: string | null;
  created_at: string;
}

export interface ByproductSaleIn {
  product_kind: SellableKind;
  buyer_id: number;
  sale_date: string; // ISO date (YYYY-MM-DD)
  kg_net: number;
  invoice_no?: string;
  price_eur?: number;
  notes?: string;
}

export interface ListSalesFilters {
  product_kind?: SellableKind;
  buyer_id?: number;
  from_date?: string;
  to_date?: string;
}

export class ByproductFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`Byproduct ${status}: ${detail}`);
    this.name = 'ByproductFetchError';
  }
}

async function readDetail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (data && typeof data.detail === 'string') return data.detail;
  } catch {
    // ignore
  }
  return res.statusText || 'Request failed';
}

async function ensureOk(res: Response): Promise<void> {
  if (!res.ok) throw new ByproductFetchError(res.status, await readDetail(res));
}

// ---------------------------------------------------------------------------
// Client-side fetchers (route through the Next.js /api/byproduct/* proxies).
// Server components should call apiGet('/byproduct/...') directly from
// '@/lib/api' for JWT pass-through via cookies(); see contract-client.ts for
// the same split.
// ---------------------------------------------------------------------------

export async function listBuyers(): Promise<ByproductBuyer[]> {
  const res = await fetch('/api/byproduct/buyers', {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  await ensureOk(res);
  return (await res.json()) as ByproductBuyer[];
}

export async function createBuyer(body: ByproductBuyerIn): Promise<ByproductBuyer> {
  const res = await fetch('/api/byproduct/buyers', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
  await ensureOk(res);
  return (await res.json()) as ByproductBuyer;
}

export async function getBuyer(buyerId: number): Promise<ByproductBuyer> {
  const res = await fetch(`/api/byproduct/buyers/${buyerId}`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  await ensureOk(res);
  return (await res.json()) as ByproductBuyer;
}

export async function updateBuyer(
  buyerId: number,
  body: ByproductBuyerPatch,
): Promise<ByproductBuyer> {
  const res = await fetch(`/api/byproduct/buyers/${buyerId}`, {
    method: 'PATCH',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
  await ensureOk(res);
  return (await res.json()) as ByproductBuyer;
}

export async function deleteBuyer(buyerId: number): Promise<void> {
  const res = await fetch(`/api/byproduct/buyers/${buyerId}`, {
    method: 'DELETE',
    credentials: 'same-origin',
    cache: 'no-store',
  });
  await ensureOk(res);
}

export async function listSales(
  filters: ListSalesFilters = {},
): Promise<ByproductSale[]> {
  const qs = new URLSearchParams();
  if (filters.product_kind) qs.set('product_kind', filters.product_kind);
  if (filters.buyer_id !== undefined) qs.set('buyer_id', String(filters.buyer_id));
  if (filters.from_date) qs.set('from_date', filters.from_date);
  if (filters.to_date) qs.set('to_date', filters.to_date);
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  const res = await fetch(`/api/byproduct/sales${suffix}`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  await ensureOk(res);
  return (await res.json()) as ByproductSale[];
}

export async function createSale(body: ByproductSaleIn): Promise<ByproductSale> {
  const res = await fetch('/api/byproduct/sales', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
  await ensureOk(res);
  return (await res.json()) as ByproductSale;
}

export async function deleteSale(saleId: number): Promise<void> {
  const res = await fetch(`/api/byproduct/sales/${saleId}`, {
    method: 'DELETE',
    credentials: 'same-origin',
    cache: 'no-store',
  });
  await ensureOk(res);
}
