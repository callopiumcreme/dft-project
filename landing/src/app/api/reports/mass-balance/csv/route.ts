import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiGet, ApiError, SESSION_COOKIE } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { rowsToCsv } from '@/lib/csv';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type DailyRow = components['schemas']['MassBalanceDailyRow'];
type MonthlyRow = components['schemas']['MassBalanceMonthlyRow'];

const DAILY_COLS: { key: keyof DailyRow; header: string }[] = [
  { key: 'day', header: 'day' },
  { key: 'input_total_kg', header: 'input_total_kg' },
  { key: 'kg_to_production', header: 'kg_to_production' },
  { key: 'eu_prod_kg', header: 'eu_prod_kg' },
  { key: 'plus_prod_kg', header: 'plus_prod_kg' },
  { key: 'carbon_black_kg', header: 'carbon_black_kg' },
  { key: 'metal_scrap_kg', header: 'metal_scrap_kg' },
  { key: 'h2o_kg', header: 'h2o_kg' },
  { key: 'gas_syngas_kg', header: 'gas_syngas_kg' },
  { key: 'losses_kg', header: 'losses_kg' },
  { key: 'output_eu_kg', header: 'output_eu_kg' },
  { key: 'output_total_kg', header: 'output_total_kg' },
  { key: 'closure_diff_pct', header: 'closure_diff_pct' },
];

const MONTHLY_COLS: { key: keyof MonthlyRow; header: string }[] = [
  { key: 'month', header: 'month' },
  { key: 'input_total_kg', header: 'input_total_kg' },
  { key: 'eu_prod_kg', header: 'eu_prod_kg' },
  { key: 'plus_prod_kg', header: 'plus_prod_kg' },
  { key: 'carbon_black_kg', header: 'carbon_black_kg' },
  { key: 'metal_scrap_kg', header: 'metal_scrap_kg' },
  { key: 'h2o_kg', header: 'h2o_kg' },
  { key: 'gas_syngas_kg', header: 'gas_syngas_kg' },
  { key: 'losses_kg', header: 'losses_kg' },
  { key: 'output_eu_kg', header: 'output_eu_kg' },
  { key: 'output_total_kg', header: 'output_total_kg' },
  { key: 'closure_diff_pct', header: 'closure_diff_pct' },
];

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function sanitizeDate(v: string | null): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
}

function sanitizeSupplierId(v: string | null): string | undefined {
  if (!v) return undefined;
  const n = Number(v);
  return Number.isInteger(n) && n > 0 ? String(n) : undefined;
}

export async function GET(req: NextRequest) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const view = req.nextUrl.searchParams.get('view') === 'monthly' ? 'monthly' : 'daily';
  const from = sanitizeDate(req.nextUrl.searchParams.get('from'));
  const to = sanitizeDate(req.nextUrl.searchParams.get('to'));
  const supplierId = sanitizeSupplierId(req.nextUrl.searchParams.get('supplier_id'));

  try {
    let csv: string;
    if (view === 'monthly') {
      const rows = await apiGet<MonthlyRow[]>('/reports/mass-balance/monthly', {
        query: { date_from: from, date_to: to, supplier_id: supplierId },
      });
      csv = rowsToCsv(rows, MONTHLY_COLS);
    } else {
      const rows = await apiGet<DailyRow[]>('/reports/mass-balance/daily', {
        query: { date_from: from, date_to: to, supplier_id: supplierId, limit: 3660 },
      });
      csv = rowsToCsv(rows, DAILY_COLS);
    }

    const filename = `mass-balance-${view}-${new Date().toISOString().slice(0, 10)}.csv`;
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
