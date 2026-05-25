import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
// DMS export MRN: 18 chars, uppercase alphanumeric (e.g. 25NL00021BHA22GMD8).
const MRN_RE = /^[0-9A-Z]{18}$/;

/**
 * Auth-gated proxy to the backend EAD PDF stream.
 * Backend route: GET /consignments/{id}/customs/{mrn}.pdf
 *
 * Files live on disk under data/customs/c-<id>/ — no Drive runtime.
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: { consignmentId: string; mrn: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const cid = decodeURIComponent(params.consignmentId);
  if (!CONSIGNMENT_ID_RE.test(cid)) {
    return NextResponse.json({ detail: 'invalid consignment id' }, { status: 400 });
  }

  const mrn = decodeURIComponent(params.mrn);
  if (!MRN_RE.test(mrn)) {
    return NextResponse.json({ detail: 'invalid MRN' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(`/consignments/${cid}/customs/${mrn}.pdf`, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'EAD PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `inline; filename="DMS_EXPORT_${mrn}.pdf"`;

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
