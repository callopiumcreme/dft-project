import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Proxies backend.app.routers.daily_inputs.doc_id_batch(). Used by the inputs
// table "Show more" path to populate the Doc ID column for rows loaded past
// the first page; the SSR initial load calls the backend directly.
export async function GET(req: NextRequest) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const ids = req.nextUrl.searchParams.get('ids') ?? '';
  if (!/^\d+(,\d+)*$/.test(ids)) {
    return NextResponse.json({ detail: 'ids must be comma-separated integers' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(`/daily-inputs/doc-id-batch?ids=${ids}`, {
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
