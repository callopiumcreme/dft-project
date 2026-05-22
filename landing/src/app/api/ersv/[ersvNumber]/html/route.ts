import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const ERSV_NUMBER_RE = /^\d{3,5}\/\d{2}$/;

export async function GET(
  req: NextRequest,
  { params }: { params: { ersvNumber: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const ersv = decodeURIComponent(params.ersvNumber);
  if (!ERSV_NUMBER_RE.test(ersv)) {
    return NextResponse.json({ detail: 'invalid eRSV format' }, { status: 400 });
  }

  const headers: Record<string, string> = { Accept: 'text/html' };
  const ifNoneMatch = req.headers.get('if-none-match');
  if (ifNoneMatch) headers['If-None-Match'] = ifNoneMatch;

  try {
    const upstream = await apiFetch(`/ersv/${encodeURIComponent(ersv)}/html`, { headers });

    if (upstream.status === 304) {
      const etag = upstream.headers.get('ETag');
      const respHeaders: Record<string, string> = { 'Cache-Control': 'no-store' };
      if (etag) respHeaders.ETag = etag;
      return new NextResponse(null, { status: 304, headers: respHeaders });
    }

    const text = await upstream.text();
    const respHeaders: Record<string, string> = {
      'Content-Type': upstream.headers.get('Content-Type') ?? 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
    };
    const etag = upstream.headers.get('ETag');
    if (etag) respHeaders.ETag = etag;

    return new NextResponse(text, { status: upstream.status, headers: respHeaders });
  } catch {
    return NextResponse.json({ detail: 'upstream error' }, { status: 502 });
  }
}
