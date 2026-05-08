import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiGet, ApiError, SESSION_COOKIE } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { rowsToCsv } from '@/lib/csv';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Row = components['schemas']['BySupplierRow'];

const COLS: { key: keyof Row; header: string }[] = [
  { key: 'supplier_id', header: 'supplier_id' },
  { key: 'supplier_code', header: 'supplier_code' },
  { key: 'supplier_name', header: 'supplier_name' },
  { key: 'total_input_kg', header: 'total_input_kg' },
  { key: 'entries', header: 'entries' },
  { key: 'days', header: 'days' },
];

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function sanitizeDate(v: string | null): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
}

export async function GET(req: NextRequest) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const from = sanitizeDate(req.nextUrl.searchParams.get('from'));
  const to = sanitizeDate(req.nextUrl.searchParams.get('to'));

  try {
    const rows = await apiGet<Row[]>('/reports/by-supplier', {
      query: { date_from: from, date_to: to },
    });
    const csv = rowsToCsv(rows, COLS);
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
