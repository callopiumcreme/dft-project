import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const SALE_ID_RE = /^\d{1,9}$/;

/**
 * Auth-gated proxy to the backend byproduct-sale invoice PDF stream.
 * Backend route: GET /byproduct/sales/{id}/pdf
 *
 * Files live on disk under backend/data/byproduct/<invoice_no>.pdf and
 * are bind-mounted into the backend container at /data/byproduct — no
 * Drive runtime. Passes `?download=1` through to flip backend
 * `Content-Disposition` from inline → attachment for the modal's
 * Download button.
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const id = decodeURIComponent(params.id);
  if (!SALE_ID_RE.test(id)) {
    return NextResponse.json({ detail: 'invalid sale id' }, { status: 400 });
  }

  const download = req.nextUrl.searchParams.get('download') === '1';
  const upstreamPath = `/byproduct/sales/${id}/pdf${
    download ? '?download=1' : ''
  }`;

  try {
    const upstream = await apiFetch(upstreamPath, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'Byproduct invoice PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `inline; filename="byproduct-sale-${id}.pdf"`;

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
