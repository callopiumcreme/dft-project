import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const ID_RE = /^\d{1,9}$/;

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { id: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  if (!ID_RE.test(params.id)) {
    return NextResponse.json({ detail: 'invalid sale id' }, { status: 400 });
  }

  try {
    const upstream = await apiFetch(`/byproduct/sales/${params.id}`, {
      method: 'DELETE',
    });
    if (upstream.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('Content-Type') ?? 'application/json',
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return NextResponse.json({ detail: 'upstream error' }, { status: 502 });
  }
}
