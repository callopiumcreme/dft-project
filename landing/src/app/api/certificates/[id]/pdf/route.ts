import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CERT_ID_RE = /^\d{1,9}$/;

/**
 * Auth-gated proxy to the backend ISCC certificate PDF stream.
 * Backend route: GET /certificates/{id}/pdf
 *
 * Files live on disk under data/certificates/ — the column
 * certificates.pdf_ref carries the relative path (no Drive runtime).
 * Path traversal is rejected by the backend; we only validate the id
 * shape here before forwarding.
 */
export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const id = decodeURIComponent(params.id);
  if (!CERT_ID_RE.test(id)) {
    return NextResponse.json({ detail: 'invalid certificate id' }, { status: 400 });
  }

  // Pass-through `?download=1` so the modal's Download button can flip
  // backend `Content-Disposition` from `inline` to `attachment`.
  const download = req.nextUrl.searchParams.get('download') === '1';
  const upstreamPath = `/certificates/${id}/pdf${download ? '?download=1' : ''}`;

  try {
    const upstream = await apiFetch(upstreamPath, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'Certificate PDF unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `inline; filename="cert_${id}.pdf"`;

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
