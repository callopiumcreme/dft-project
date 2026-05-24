import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
const POS_NUMBER_RE = /^[A-Z0-9-]{1,40}$/;

export async function GET(
  _req: NextRequest,
  { params }: { params: { consignmentId: string; posNumber: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const cid = decodeURIComponent(params.consignmentId);
  if (!CONSIGNMENT_ID_RE.test(cid)) {
    return NextResponse.json({ detail: 'invalid consignment id' }, { status: 400 });
  }

  const pos = decodeURIComponent(params.posNumber);
  if (!POS_NUMBER_RE.test(pos)) {
    return NextResponse.json({ detail: 'invalid PoS number' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(
      `/ersv/outbound/${cid}/${encodeURIComponent(pos)}?format=pdf`,
      { headers: { Accept: 'application/pdf' } },
    );

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'eRSV PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `attachment; filename="ersv-outbound-${cid}-${pos}.pdf"`;

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
