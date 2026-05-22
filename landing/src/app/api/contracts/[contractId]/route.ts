import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { apiFetch, SESSION_COOKIE } from '@/lib/api';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CONTRACT_ID_RE = /^\d{1,9}$/;

export async function GET(
  req: NextRequest,
  { params }: { params: { contractId: string } },
) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: 'unauthorized' }, { status: 401 });

  if (!CONTRACT_ID_RE.test(params.contractId)) {
    return NextResponse.json({ detail: 'invalid contract id' }, { status: 400 });
  }

  const includeDeleted = req.nextUrl.searchParams.get('include_deleted');
  const qs = includeDeleted === 'true' ? '?include_deleted=true' : '';

  try {
    const upstream = await apiFetch(`/contracts/${params.contractId}${qs}`, {
      headers: { Accept: 'application/json' },
    });
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
