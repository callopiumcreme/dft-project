export const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
export const POS_NUMBER_RE = /^[A-Z0-9-]{1,40}$/;

export class ErsvOutboundNotFoundError extends Error {
  constructor(
    public readonly consignmentId: number,
    public readonly posNumber: string,
  ) {
    super(`Outbound eRSV ${consignmentId}/${posNumber} not found`);
    this.name = 'ErsvOutboundNotFoundError';
  }
}

export class ErsvOutboundFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`Outbound eRSV fetch failed (${status}): ${detail}`);
    this.name = 'ErsvOutboundFetchError';
  }
}

function assertValidConsignment(consignmentId: number): void {
  if (!Number.isInteger(consignmentId) || !CONSIGNMENT_ID_RE.test(String(consignmentId))) {
    throw new ErsvOutboundFetchError(400, `Invalid consignment id: ${consignmentId}`);
  }
}

function assertValidPos(posNumber: string): void {
  if (!POS_NUMBER_RE.test(posNumber)) {
    throw new ErsvOutboundFetchError(400, `Invalid PoS number format: ${posNumber}`);
  }
}

function encodePos(posNumber: string): string {
  return encodeURIComponent(posNumber);
}

function cacheKey(consignmentId: number, posNumber: string): string {
  return `${consignmentId}#${posNumber}`;
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

const htmlCache: Map<string, HtmlCacheEntry> = new Map();

export async function fetchOutboundErsvHtml(
  consignmentId: number,
  posNumber: string,
): Promise<{ html: string; etag: string | null }> {
  assertValidConsignment(consignmentId);
  assertValidPos(posNumber);

  const key = cacheKey(consignmentId, posNumber);
  const cached = htmlCache.get(key);
  const headers: Record<string, string> = { Accept: 'text/html' };
  if (cached) headers['If-None-Match'] = cached.etag;

  const res = await fetch(
    `/api/ersv-outbound/${consignmentId}/${encodePos(posNumber)}/html`,
    {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers,
    },
  );

  if (res.status === 304 && cached) {
    return { html: cached.html, etag: cached.etag };
  }
  if (res.status === 404) throw new ErsvOutboundNotFoundError(consignmentId, posNumber);
  if (!res.ok) throw new ErsvOutboundFetchError(res.status, await readDetail(res));

  const html = await res.text();
  const etag = res.headers.get('ETag');
  if (etag) htmlCache.set(key, { etag, html });
  return { html, etag };
}

export function buildOutboundErsvPdfUrl(
  consignmentId: number,
  posNumber: string,
): string {
  assertValidConsignment(consignmentId);
  assertValidPos(posNumber);
  return `/api/ersv-outbound/${consignmentId}/${encodePos(posNumber)}/pdf`;
}
