import { NextRequest, NextResponse } from 'next/server';
import { Resend } from 'resend';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// ── Rate limiter (in-memory, per IP) ────────────────────────────────────────
const WINDOW_MS = 10 * 60 * 1000; // 10 min
const MAX_PER_WINDOW = 3;
const rateMap = new Map<string, { hits: number; resetAt: number }>();
let lastClean = 0;

function rateLimited(ip: string): boolean {
  const now = Date.now();
  // Periodic stale-entry cleanup
  if (now - lastClean > WINDOW_MS) {
    for (const [k, v] of rateMap) if (now > v.resetAt) rateMap.delete(k);
    lastClean = now;
  }
  const entry = rateMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateMap.set(ip, { hits: 1, resetAt: now + WINDOW_MS });
    return false;
  }
  if (entry.hits >= MAX_PER_WINDOW) return true;
  entry.hits++;
  return false;
}

// ── Input sanitization ───────────────────────────────────────────────────────
// Strip \r\n (email header injection) and < > (HTML injection)
function clean(v: unknown, max = 500): string {
  if (typeof v !== 'string') return '';
  return v
    .replace(/[\r\n]/g, ' ')
    .replace(/[<>]/g, '')
    .trim()
    .slice(0, max);
}

function isValidEmail(s: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

type ContactPayload = {
  name?: unknown;
  email?: unknown;
  company?: unknown;
  role?: unknown;
  message?: unknown;
  website?: unknown;
};

export async function POST(request: NextRequest) {
  const ip =
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    request.headers.get('x-real-ip') ??
    'unknown';

  if (rateLimited(ip)) {
    return NextResponse.json(
      { error: 'Too many requests. Please try again later.' },
      { status: 429 }
    );
  }

  let body: ContactPayload;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  // Honeypot: silently accept but do nothing
  if (body.website && String(body.website).length > 0) {
    return NextResponse.json({ ok: true });
  }

  const name = clean(body.name, 200);
  const email = clean(body.email, 254);
  const message = clean(body.message, 5000);
  const company = clean(body.company, 200) || '—';
  const role = clean(body.role, 200) || '—';

  if (!name || !email || !message) {
    return NextResponse.json(
      { error: 'Name, email and message are required.' },
      { status: 400 }
    );
  }
  if (!isValidEmail(email)) {
    return NextResponse.json({ error: 'Invalid email.' }, { status: 400 });
  }

  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.CONTACT_FROM ?? 'DFT <hello@dft-project.com>';
  const to = process.env.CONTACT_TO ?? 'hello@dft-project.com';

  if (!apiKey) {
    console.warn('[contact] RESEND_API_KEY not set — logging payload only');
    console.info('[contact]', { name, email, company, role });
    return NextResponse.json({ ok: true, dev: true });
  }

  try {
    const resend = new Resend(apiKey);

    const result = await resend.emails.send({
      from,
      to,
      replyTo: email,
      subject: `[DFT] Contact · ${name} · ${company}`,
      text: [
        `Name:    ${name}`,
        `Email:   ${email}`,
        `Company: ${company}`,
        `Role:    ${role}`,
        '',
        '---',
        message,
      ].join('\n'),
    });

    if ('error' in result && result.error) {
      console.error('[contact] resend error', result.error);
      return NextResponse.json(
        { error: 'Email service unavailable.' },
        { status: 502 }
      );
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('[contact]', err);
    return NextResponse.json(
      { error: 'Email service unavailable.' },
      { status: 502 }
    );
  }
}
