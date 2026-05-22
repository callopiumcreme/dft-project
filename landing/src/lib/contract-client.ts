export const CONTRACT_CODE_RE = /^[A-Z0-9_-]{1,32}$/;

export interface ContractDetail {
  id: number;
  code: string;
  supplier_id: number | null;
  start_date: string | null;
  end_date: string | null;
  total_kg_committed: string | null;
  is_placeholder: boolean;
  notes: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export class ContractNotFoundError extends Error {
  constructor(public readonly contractId: number) {
    super(`Contract ${contractId} PDF not found`);
    this.name = 'ContractNotFoundError';
  }
}

export class ContractFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`Contract fetch failed (${status}): ${detail}`);
    this.name = 'ContractFetchError';
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

export async function fetchContractMetadata(contractId: number): Promise<ContractDetail> {
  const res = await fetch(`/api/contracts/${contractId}?include_deleted=true`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (res.status === 404) throw new ContractNotFoundError(contractId);
  if (!res.ok) throw new ContractFetchError(res.status, await readDetail(res));
  return (await res.json()) as ContractDetail;
}

export async function probeContractPdf(contractId: number): Promise<boolean> {
  const res = await fetch(`/api/contracts/${contractId}/pdf`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Range: 'bytes=0-0' },
  });
  return res.ok || res.status === 206;
}

export function buildContractPdfUrl(contractId: number): string {
  return `/api/contracts/${contractId}/pdf`;
}

export function buildContractDownloadUrl(contractId: number): string {
  return `/api/contracts/${contractId}/pdf/download`;
}
