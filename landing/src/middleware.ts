import { NextResponse, type NextRequest } from 'next/server';
import { jwtVerify, errors as joseErrors } from 'jose';

const SESSION_COOKIE = 'dft_session';
const ALG = 'HS256';

const SECRET_KEY = new TextEncoder().encode(
  process.env.JWT_SECRET ?? 'changeme-dft-secret-key-2026',
);

function isSafeNext(path: string): boolean {
  return path.startsWith('/') && !path.startsWith('//') && !path.startsWith('/\\');
}

export async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const token = req.cookies.get(SESSION_COOKIE)?.value;

  const loginUrl = new URL('/login', req.url);
  const nextPath = pathname + search;
  if (isSafeNext(nextPath) && nextPath !== '/login') {
    loginUrl.searchParams.set('next', nextPath);
  }

  if (!token) {
    return NextResponse.redirect(loginUrl);
  }

  try {
    const { payload } = await jwtVerify(token, SECRET_KEY, { algorithms: [ALG] });
    const res = NextResponse.next();
    if (typeof payload.role === 'string') res.headers.set('x-user-role', payload.role);
    if (typeof payload.sub === 'string') res.headers.set('x-user-email', payload.sub);
    return res;
  } catch (e) {
    const expired = e instanceof joseErrors.JWTExpired;
    if (expired) loginUrl.searchParams.set('expired', '1');
    const res = NextResponse.redirect(loginUrl);
    res.cookies.delete(SESSION_COOKIE);
    return res;
  }
}

export const config = {
  matcher: ['/app', '/app/:path*'],
};
