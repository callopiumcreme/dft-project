import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
// OisteBio commercial invoice number to Crown Oil Ltd: `OIS-INV<digits>`
// (e.g. OIS-INV250023). Anchored strictly to prevent path-traversal.
const INVOICE_RE = /^OIS-INV\d{4,12}$/;

/**
 * Auth-gated proxy to the backend commercial-invoice PDF stream.
 * Backend route: GET /consignments/{id}/invoices/{invoice_no}.pdf
 *
 * Files live on disk under data/invoices/c-<id>/ — no Drive runtime.
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { consignmentId: string; invoiceNo: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const cid = decodeURIComponent(params.consignmentId);
  if (!CONSIGNMENT_ID_RE.test(cid)) {
    return NextResponse.json({ detail: 'invalid consignment id' }, { status: 400 });
  }

  const inv = decodeURIComponent(params.invoiceNo);
  if (!INVOICE_RE.test(inv)) {
    return NextResponse.json({ detail: 'invalid invoice number' }, { status: 400 });
  }

  // Pass-through `?download=1` so the modal's Download button can flip
  // backend `Content-Disposition` from `inline` to `attachment`.
  const download = req.nextUrl.searchParams.get('download') === '1';
  const upstreamPath = `/consignments/${cid}/invoices/${inv}.pdf${
    download ? '?download=1' : ''
  }`;

  try {
    const upstream = await apiFetch(upstreamPath, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'Invoice PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `inline; filename="INV_${inv}.pdf"`;

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
