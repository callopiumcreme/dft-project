export const SHIPMENT_ID_RE = /^\d{1,9}$/;

export class ErsvInlandNotFoundError extends Error {
  constructor(public readonly shipmentId: number) {
    super(`Inland eRSV ${shipmentId} not found`);
    this.name = 'ErsvInlandNotFoundError';
  }
}

export class ErsvInlandFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`Inland eRSV fetch failed (${status}): ${detail}`);
    this.name = 'ErsvInlandFetchError';
  }
}

function assertValidId(shipmentId: number): void {
  if (!Number.isInteger(shipmentId) || !SHIPMENT_ID_RE.test(String(shipmentId))) {
    throw new ErsvInlandFetchError(400, `Invalid shipment id: ${shipmentId}`);
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

interface HtmlCacheEntry {
  etag: string;
  html: string;
}

const htmlCache: Map<number, HtmlCacheEntry> = new Map();

export async function fetchInlandErsvHtml(
  shipmentId: number,
): Promise<{ html: string; etag: string | null }> {
  assertValidId(shipmentId);

  const cached = htmlCache.get(shipmentId);
  const headers: Record<string, string> = { Accept: 'text/html' };
  if (cached) headers['If-None-Match'] = cached.etag;

  const res = await fetch(`/api/ersv-inland/${shipmentId}/html`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers,
  });

  if (res.status === 304 && cached) {
    return { html: cached.html, etag: cached.etag };
  }
  if (res.status === 404) throw new ErsvInlandNotFoundError(shipmentId);
  if (!res.ok) throw new ErsvInlandFetchError(res.status, await readDetail(res));

  const html = await res.text();
  const etag = res.headers.get('ETag');
  if (etag) htmlCache.set(shipmentId, { etag, html });
  return { html, etag };
}

export function buildInlandErsvPdfUrl(shipmentId: number): string {
  assertValidId(shipmentId);
  return `/api/ersv-inland/${shipmentId}/pdf`;
}
