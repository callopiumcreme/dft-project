import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiGet, ApiError, SESSION_COOKIE } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { rowsToCsv } from '@/lib/csv';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type Row = components['schemas']['ClosureStatusRow'];

const COLS: { key: keyof Row; header: string }[] = [
  { key: 'day', header: 'day' },
  { key: 'input_total_kg', header: 'input_total_kg' },
  { key: 'output_total_kg', header: 'output_total_kg' },
  { key: 'closure_diff_pct', header: 'closure_diff_pct' },
  { key: 'bucket', header: 'bucket' },
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
  const bucket = req.nextUrl.searchParams.get('bucket');

  try {
    let rows = await apiGet<Row[]>('/reports/closure-status', {
      query: { date_from: from, date_to: to },
    });
    if (bucket && ['ok', 'warn', 'alert', 'no_input', 'no_output'].includes(bucket)) {
      rows = rows.filter((r) => r.bucket === bucket);
    }
    const csv = rowsToCsv(rows, COLS);
    const filename = `closure-status-${new Date().toISOString().slice(0, 10)}.csv`;
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
