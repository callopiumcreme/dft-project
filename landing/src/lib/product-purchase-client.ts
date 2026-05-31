export const POS_NUMBER_RE = /^[A-Z0-9_-]{1,40}$/;

export interface ProductPurchaseDetail {
  id: number;
  pos_number: string;
  supplier_id: number | null;
  supplier_name: string | null;
  certificate_id: number | null;
  contract_id: number | null;
  issuance_date: string | null;
  dispatch_label: string | null;
  quantity_kg: string | null;
  feedstock: string | null;
  notes: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export class ProductPurchaseNotFoundError extends Error {
  constructor(public readonly ppId: number) {
    super(`Product purchase ${ppId} PDF not found`);
    this.name = 'ProductPurchaseNotFoundError';
  }
}

export class ProductPurchaseFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`Product purchase fetch failed (${status}): ${detail}`);
    this.name = 'ProductPurchaseFetchError';
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

export async function fetchProductPurchaseMetadata(
  ppId: number,
): Promise<ProductPurchaseDetail> {
  const res = await fetch(`/api/product-purchases/${ppId}?include_deleted=true`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (res.status === 404) throw new ProductPurchaseNotFoundError(ppId);
  if (!res.ok) throw new ProductPurchaseFetchError(res.status, await readDetail(res));
  return (await res.json()) as ProductPurchaseDetail;
}

export async function probeProductPurchasePdf(ppId: number): Promise<boolean> {
  const res = await fetch(`/api/product-purchases/${ppId}/pdf`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Range: 'bytes=0-0' },
  });
  return res.ok || res.status === 206;
}

export function buildProductPurchasePdfUrl(ppId: number): string {
  return `/api/product-purchases/${ppId}/pdf`;
}

export function buildProductPurchaseDownloadUrl(ppId: number): string {
  return `/api/product-purchases/${ppId}/pdf/download`;
}
