import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const SALE_ID_RE = /^\d{1,9}$/;

/**
 * Auth-gated proxy to the backend POS PDF stream paired with a virtual
 * Crown DEV-P100 byproduct-sale row.
 *
 * Backend route: GET /byproduct/sales/{id}/pos.pdf (only valid for
 * sale_id >= CUSTOMS_VIRTUAL_OFFSET — canonical byproduct_sale rows have
 * no POS counterpart and the backend returns 400 there).
 *
 * The local URL keeps a dot-free folder name (`/pos`) to stay safe with
 * Next.js App Router segment conventions; the mapping to the backend
 * `pos.pdf` filename happens here.
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
  const upstreamPath = `/byproduct/sales/${id}/pos.pdf${
    download ? '?download=1' : ''
  }`;

  try {
    const upstream = await apiFetch(upstreamPath, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'POS PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `inline; filename="pos-${id}.pdf"`;

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
