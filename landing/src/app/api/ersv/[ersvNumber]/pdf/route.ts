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
    const upstream = await apiFetch(`/ersv/${encodeURIComponent(ersv)}/pdf`, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'eRSV PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const filenameSafe = ersv.replace('/', '-');
    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `attachment; filename="ersv-${filenameSafe}.pdf"`;

    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') ?? 'application/pdf',
        'Content-Disposition': disposition,
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return NextResponse.json({ detail: 'upstream error' }, { status: 502 });
  }
}
