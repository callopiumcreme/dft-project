import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiGet, ApiError, SESSION_COOKIE } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { rowsToCsv } from '@/lib/csv';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Row = components['schemas']['BySupplierRow'];

const REDIST_POOL = new Set(['EFFICIEN', 'KALTIRE', 'PYRCOM', 'BOLDER', 'ESENTTIA']);
const REDIST_TARGET: Record<string, number> = {
  EFFICIEN: 35,
  KALTIRE: 30,
  PYRCOM: 20,
  BOLDER: 10,
  ESENTTIA: 5,
};

type EnrichedRow = Row & { pct_total: string; pct_pool: string; target_pct: string };

const COLS: { key: keyof EnrichedRow; header: string }[] = [
  { key: 'supplier_id', header: 'supplier_id' },
  { key: 'supplier_code', header: 'supplier_code' },
  { key: 'supplier_name', header: 'supplier_name' },
  { key: 'total_input_kg', header: 'total_input_kg' },
  { key: 'pct_total', header: 'pct_total' },
  { key: 'pct_pool', header: 'pct_pool' },
  { key: 'target_pct', header: 'target_pct' },
  { key: 'entries', header: 'entries' },
  { key: 'days', header: 'days' },
];

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const REDIST_FROM = '2025-02-01';
const REDIST_TO = '2025-08-31';

function sanitizeDate(v: string | null): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
}

export async function GET(req: NextRequest) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const sp = req.nextUrl.searchParams;
  const scope = sp.get('scope');
  const hasExplicitDates = sp.has('from') || sp.has('to');
  const useAll = scope === 'all';
  let from: string | undefined;
  let to: string | undefined;
  if (useAll) {
    from = undefined;
    to = undefined;
  } else if (hasExplicitDates) {
    from = sanitizeDate(sp.get('from'));
    to = sanitizeDate(sp.get('to'));
  } else {
    from = REDIST_FROM;
    to = REDIST_TO;
  }

  try {
    const rows = await apiGet<Row[]>('/reports/by-supplier', {
      query: { date_from: from, date_to: to },
    });
    const totalKg = rows.reduce((s, r) => s + (Number(r.total_input_kg) || 0), 0);
    const poolKg = rows
      .filter((r) => REDIST_POOL.has(r.supplier_code))
      .reduce((s, r) => s + (Number(r.total_input_kg) || 0), 0);
    const enriched: EnrichedRow[] = rows.map((r) => {
      const v = Number(r.total_input_kg) || 0;
      const inPool = REDIST_POOL.has(r.supplier_code);
      const pctTotal = totalKg > 0 ? (v / totalKg) * 100 : 0;
      const pctPool = inPool && poolKg > 0 ? (v / poolKg) * 100 : null;
      const target = REDIST_TARGET[r.supplier_code];
      return {
        ...r,
        pct_total: pctTotal.toFixed(4),
        pct_pool: pctPool === null ? '' : pctPool.toFixed(4),
        target_pct: target === undefined ? '' : target.toFixed(4),
      };
    });
    const csv = rowsToCsv(enriched, COLS);
    const filename = `by-supplier-${new Date().toISOString().slice(0, 10)}.csv`;
    return new NextResponse(csv, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Cache-Control': 'no-store',
      },
    });
  } catch (e) {
    if (e instanceof ApiError) {
      return NextResponse.json({ detail: e.detail }, { status: e.status });
    }
    return NextResponse.json({ detail: 'export failed' }, { status: 500 });
  }
}
