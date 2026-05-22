import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function parseId(raw: string): number | null {
  const n = Number(raw);
  if (!Number.isInteger(n) || n <= 0) return null;
  return n;
}

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  const id = parseId(params.id);
  if (id === null) {
    return NextResponse.json({ detail: 'invalid ticket id' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(`/tickets/${id}/escpos`, {
      headers: { Accept: 'application/octet-stream' },
    });

    if (!upstream.ok || !upstream.body) {
      const text = await upstream.text().catch(() => '');
      return new NextResponse(text || 'ticket ESC/POS unavailable', {
        status: upstream.status || 502,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      });
    }

    const upstreamDisposition = upstream.headers.get('Content-Disposition');
    const disposition =
      upstreamDisposition ?? `attachment; filename="ticket_${id}.escpos"`;

    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') ?? 'application/octet-stream',
        'Content-Disposition': disposition,
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return NextResponse.json({ detail: 'upstream error' }, { status: 502 });
  }
}
