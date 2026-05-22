export const ERSV_NUMBER_RE = /^\d{3,5}\/\d{2}$/;

export interface ErsvDetail {
  ersv_number: string;
  daily_input_id: number;
  entry_date: string;
  entry_time: string | null;
  supplier_id: number;
  supplier_code: string;
  supplier_name: string;
  total_input_kg: string | number;
  car_kg: string | number | null;
  truck_kg: string | number | null;
  special_kg: string | number | null;
  cert_iscc_ref: string | null;
  is_regenerated: boolean;
  rectified_at: string | null;
  rectification_reason: string | null;
  updated_at: string;
}

export class ErsvNotFoundError extends Error {
  constructor(public readonly ersvNumber: string) {
    super(`eRSV ${ersvNumber} not found`);
    this.name = 'ErsvNotFoundError';
  }
}

export class ErsvFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`eRSV fetch failed (${status}): ${detail}`);
    this.name = 'ErsvFetchError';
  }
}

function assertValidErsv(ersvNumber: string): void {
  if (!ERSV_NUMBER_RE.test(ersvNumber)) {
    throw new ErsvFetchError(400, `Invalid eRSV format: ${ersvNumber}`);
  }
}

function encode(ersvNumber: string): string {
  return encodeURIComponent(ersvNumber);
}

function withId(path: string, dailyInputId?: number | null): string {
  if (dailyInputId == null) return path;
  const sep = path.includes('?') ? '&' : '?';
  return `${path}${sep}daily_input_id=${dailyInputId}`;
}

function cacheKey(ersvNumber: string, dailyInputId?: number | null): string {
  return dailyInputId == null ? ersvNumber : `${ersvNumber}#${dailyInputId}`;
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

export async function fetchErsvMetadata(
  ersvNumber: string,
  dailyInputId?: number | null,
): Promise<ErsvDetail> {
  assertValidErsv(ersvNumber);
  const res = await fetch(withId(`/api/ersv/${encode(ersvNumber)}`, dailyInputId), {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (res.status === 404) throw new ErsvNotFoundError(ersvNumber);
  if (!res.ok) throw new ErsvFetchError(res.status, await readDetail(res));
  return (await res.json()) as ErsvDetail;
}

interface HtmlCacheEntry {
  etag: string;
  html: string;
}

const htmlCache: Map<string, HtmlCacheEntry> = new Map();

export async function fetchErsvHtml(
  ersvNumber: string,
  dailyInputId?: number | null,
): Promise<{ html: string; etag: string | null }> {
  assertValidErsv(ersvNumber);
  const key = cacheKey(ersvNumber, dailyInputId);
  const cached = htmlCache.get(key);
  const headers: Record<string, string> = { Accept: 'text/html' };
  if (cached) headers['If-None-Match'] = cached.etag;

  const res = await fetch(withId(`/api/ersv/${encode(ersvNumber)}/html`, dailyInputId), {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers,
  });

  if (res.status === 304 && cached) {
    return { html: cached.html, etag: cached.etag };
  }
  if (res.status === 404) throw new ErsvNotFoundError(ersvNumber);
  if (!res.ok) throw new ErsvFetchError(res.status, await readDetail(res));

  const html = await res.text();
  const etag = res.headers.get('ETag');
  if (etag) htmlCache.set(key, { etag, html });
  return { html, etag };
}

export function buildErsvPdfUrl(ersvNumber: string, dailyInputId?: number | null): string {
  assertValidErsv(ersvNumber);
  return withId(`/api/ersv/${encode(ersvNumber)}/pdf`, dailyInputId);
}
