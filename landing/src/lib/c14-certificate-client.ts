export const C14_NUMBER_RE = /^[A-Z0-9_-]{1,40}$/;

export interface C14CertificateDetail {
  id: number;
  cert_number: string;
  lab: string | null;
  product: string | null;
  period_month: string | null;
  sampled_date: string | null;
  tested_date: string | null;
  report_date: string | null;
  bio_carbon_pct: string | null;
  method: string | null;
  sample_ref: string | null;
  batch_ref: string | null;
  sustainability_decl: string | null;
  pdf_filename: string | null;
  notes: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export class C14CertificateNotFoundError extends Error {
  constructor(public readonly c14Id: number) {
    super(`C14 certificate ${c14Id} PDF not found`);
    this.name = 'C14CertificateNotFoundError';
  }
}

export class C14CertificateFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`C14 certificate fetch failed (${status}): ${detail}`);
    this.name = 'C14CertificateFetchError';
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

export async function fetchC14CertificateMetadata(
  c14Id: number,
): Promise<C14CertificateDetail> {
  const res = await fetch(`/api/c14-certificates/${c14Id}?include_deleted=true`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (res.status === 404) throw new C14CertificateNotFoundError(c14Id);
  if (!res.ok) throw new C14CertificateFetchError(res.status, await readDetail(res));
  return (await res.json()) as C14CertificateDetail;
}

export async function probeC14CertificatePdf(c14Id: number): Promise<boolean> {
  const res = await fetch(`/api/c14-certificates/${c14Id}/pdf`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Range: 'bytes=0-0' },
  });
  return res.ok || res.status === 206;
}

export function buildC14CertificatePdfUrl(c14Id: number): string {
  return `/api/c14-certificates/${c14Id}/pdf`;
}

export function buildC14CertificateDownloadUrl(c14Id: number): string {
  return `/api/c14-certificates/${c14Id}/pdf/download`;
}
