import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
// Transload consolidated-report reference — same anchor as the backend
// regex: e.g. UTB-2025-Q3-CONSOLIDATED. Uppercase letters/digits with
// single-hyphen separators, max 9 segments. Strict pattern prevents
// path-traversal at the landing-proxy layer before the request reaches
// the backend's own Path.resolve().relative_to(root) guard.
const TRANSLOAD_REF_RE = /^[A-Z0-9]+(?:-[A-Z0-9]+){0,8}$/;

/**
 * Auth-gated proxy to the backend UTB transload PDF stream.
 * Backend route: GET /consignments/{id}/transload/{ref}.pdf
 *
 * Files live on disk under data/transload/c-<id>/ — no Drive runtime.
 * The artefact ``UTB-2025-Q3-CONSOLIDATED.pdf`` is rendered out-of-band
 * by ``scripts/render_transload_consolidated.py`` (deterministic PDF).
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string; ref: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const cid = decodeURIComponent(params.id);
  if (!CONSIGNMENT_ID_RE.test(cid)) {
    return NextResponse.json({ detail: 'invalid consignment id' }, { status: 400 });
  }

  const ref = decodeURIComponent(params.ref);
  if (!TRANSLOAD_REF_RE.test(ref)) {
    return NextResponse.json({ detail: 'invalid transload ref' }, { status: 400 });
  }

  // Pass-through ?download=1 so the modal's Download button flips
  // backend Content-Disposition from inline to attachment.
  const download = req.nextUrl.searchParams.get('download') === '1';
  const upstreamPath = `/consignments/${cid}/transload/${ref}.pdf${
    download ? '?download=1' : ''
  }`;

  try {
    const upstream = await apiFetch(upstreamPath, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'Transload PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `inline; filename="${ref}.pdf"`;

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
