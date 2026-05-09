import type { Metadata } from 'next';
import Link from 'next/link';
import { LoginForm } from './login-form';

export const metadata: Metadata = {
  title: 'Login — DFT',
  robots: { index: false, follow: false },
};

function safeNext(raw: string | string[] | undefined): string {
  if (typeof raw !== 'string') return '/app';
  if (!raw.startsWith('/')) return '/app';
  if (raw.startsWith('//') || raw.startsWith('/\\')) return '/app';
  if (raw === '/login') return '/app';
  return raw;
}

type SearchParams = { next?: string | string[]; expired?: string | string[] };

export default function LoginPage({ searchParams }: { searchParams: SearchParams }) {
  const next = safeNext(searchParams.next);
  const expired = searchParams.expired === '1';

  return (
    <main className="min-h-dvh grid place-items-center bg-bg px-6 py-16">
      <div className="w-full max-w-sm">
        <Link
          href="/"
          className="font-display text-3xl tracking-editorial text-ink hover:text-olive-deep transition-colors"
        >
          DFT
        </Link>
        <p className="mt-2 mb-12 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Mass balance — operator access
        </p>
        {expired && (
          <p
            role="status"
            className="mb-6 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-accent"
          >
            Session expired · sign in again
          </p>
        )}
        <LoginForm next={next} />
        <p className="mt-12 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          8h session · httpOnly cookie
        </p>
      </div>
    </main>
  );
}
