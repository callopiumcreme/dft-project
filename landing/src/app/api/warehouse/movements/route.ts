import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Mirrors backend.app.routers.warehouse.list_warehouse_movements() query
// params. limit + offset support the client-side "Show more" pagination.
const ALLOWED_QS = new Set(['limit', 'offset', 'product_kind', 'event_type']);

export async function GET(req: NextRequest) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const forwardQs = new URLSearchParams();
  for (const [k, v] of req.nextUrl.searchParams.entries()) {
    if (ALLOWED_QS.has(k) && v) forwardQs.append(k, v);
  }
  const suffix = forwardQs.toString() ? `?${forwardQs.toString()}` : '';

  try {
    const upstream = await apiFetch(`/warehouse/movements${suffix}`, {
      headers: { Accept: 'application/json' },
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') ?? 'application/json',
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return NextResponse.json({ detail: 'upstream error' }, { status: 502 });
  }
}
