import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
// Ocean BL number: SCAC carrier code (4 uppercase letters) + 6–12 digits
// (e.g. CMDU for CMA-CGM, MAEU for Maersk, MEDU for MSC, HLCU for
// Hapag-Lloyd). Anchored strictly to prevent path-traversal at the
// landing proxy before the request hits backend.
const BL_OCEAN_RE = /^[A-Z]{4}\d{6,12}$/;

/**
 * Auth-gated proxy to the backend Ocean BL PDF stream.
 * Backend route: GET /consignments/{id}/bl/{bl_no}.pdf
 *
 * Files live on disk under data/bl_ocean/c-<id>/ — no Drive runtime.
 * Filenames preserve Drive provenance (`BL_<no>_<VESSEL>_<YYYY-MM-DD>.pdf`)
 * for audit trail continuity (ISCC EU + DfT RTFO).
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string; blNo: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const cid = decodeURIComponent(params.id);
  if (!CONSIGNMENT_ID_RE.test(cid)) {
    return NextResponse.json({ detail: 'invalid consignment id' }, { status: 400 });
  }

  const bl = decodeURIComponent(params.blNo);
  if (!BL_OCEAN_RE.test(bl)) {
    return NextResponse.json({ detail: 'invalid BL number' }, { status: 400 });
  }

  // Pass-through `?download=1` so the modal's Download button can flip
  // backend `Content-Disposition` from `inline` to `attachment`.
  const download = req.nextUrl.searchParams.get('download') === '1';
  const upstreamPath = `/consignments/${cid}/bl/${bl}.pdf${
    download ? '?download=1' : ''
  }`;

  try {
    const upstream = await apiFetch(upstreamPath, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'BL PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `inline; filename="BL_${bl}.pdf"`;

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
