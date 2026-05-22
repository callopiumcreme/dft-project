import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const ERSV_NUMBER_RE = /^\d{3,5}\/\d{2}$/;

export async function GET(
  _req: NextRequest,
  { params }: { params: { ersvNumber: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const ersv = decodeURIComponent(params.ersvNumber);
  if (!ERSV_NUMBER_RE.test(ersv)) {
    return NextResponse.json({ detail: 'invalid eRSV format' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(`/ersv/${encodeURIComponent(ersv)}`, {
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
