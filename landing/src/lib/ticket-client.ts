export interface TicketDetail {
  daily_input_id: number;
  ersv_number: string | null;
  entry_date: string;
  supplier_code: string;
  supplier_name: string;
  prod: 'LLANTAS' | 'SPECIAL';
  total_input_kg: string | number;
  driver_name: string;
  driver_cedula: string;
  vehicle_plate: string;
  transport_company: string;
  hora_ent: string;
  hora_sal: string;
  peso_ent_kg: string | number;
  peso_sal_kg: string | number;
  peso_neto_kg: string | number;
  ticket_num: number;
  weigher: string;
  preview_text: string;
}

export class TicketNotFoundError extends Error {
  constructor(public readonly dailyInputId: number) {
    super(`Ticket for daily input ${dailyInputId} not found`);
    this.name = 'TicketNotFoundError';
  }
}

export class TicketFetchError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`Ticket fetch failed (${status}): ${detail}`);
    this.name = 'TicketFetchError';
  }
}

function assertValidId(dailyInputId: number): void {
  if (!Number.isInteger(dailyInputId) || dailyInputId <= 0) {
    throw new TicketFetchError(400, `Invalid daily input id: ${dailyInputId}`);
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

export async function fetchTicketMetadata(dailyInputId: number): Promise<TicketDetail> {
  assertValidId(dailyInputId);
  const res = await fetch(`/api/tickets/${dailyInputId}`, {
    method: 'GET',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (res.status === 404) throw new TicketNotFoundError(dailyInputId);
  if (!res.ok) throw new TicketFetchError(res.status, await readDetail(res));
  return (await res.json()) as TicketDetail;
}

export function buildTicketEscposUrl(dailyInputId: number): string {
  assertValidId(dailyInputId);
  return `/api/tickets/${dailyInputId}/escpos`;
}
