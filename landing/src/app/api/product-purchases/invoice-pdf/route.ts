import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Drive filename as carried in pos-invoice-map (letters, digits, space, . _ - ( ) ).
const FILE_RE = /^[A-Za-z0-9 ._()-]{1,100}\.pdf$/;

export async function GET(req: NextRequest) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const file = req.nextUrl.searchParams.get('file') ?? '';
  if (!FILE_RE.test(file)) {
    return NextResponse.json({ detail: 'invalid invoice file' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(
      `/product-purchases/invoice-pdf?file=${encodeURIComponent(file)}`,
      { headers: { Accept: 'application/pdf' } },
    );

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'Invoice PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const disposition =
      upstream.headers.get('Content-Disposition') ?? `inline; filename="${file}"`;

    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') ?? 'application/pdf',
        'Content-Disposition': disposition,
        'Cache-Control': 'private, max-age=300',
      },
    });
  } catch {
    return NextResponse.json({ detail: 'upstream error' }, { status: 502 });
  }
}
