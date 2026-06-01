import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// On-the-fly proforma / supply-data-sheet for a single PoS, proxied from the
// backend renderer. Inline PDF preview for the modal iframe (no audit upstream).
export async function GET(
  req: NextRequest,
  { params }: { params: { ppId: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const ppId = Number(params.ppId);
  if (!Number.isInteger(ppId) || ppId <= 0) {
    return NextResponse.json({ detail: 'invalid id' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(`/product-purchases/${ppId}/proforma?format=pdf`, {
      headers: { Accept: 'application/pdf' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'Proforma unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') ?? 'application/pdf',
        'Content-Disposition':
          upstream.headers.get('Content-Disposition') ??
          `inline; filename="proforma_${ppId}.pdf"`,
        'Cache-Control': 'private, max-age=120',
      },
    });
  } catch {
    return NextResponse.json({ detail: 'upstream error' }, { status: 502 });
  }
}
