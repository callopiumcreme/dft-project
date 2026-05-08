import type { Metadata } from 'next';
import Link from 'next/link';
import { LoginForm } from './login-form';

export const metadata: Metadata = {
  title: 'Login — DFT',
  robots: { index: false, follow: false },
};

export default function LoginPage() {
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
          Mass balance — accesso operatori
        </p>
        <LoginForm />
        <p className="mt-12 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Sessione 8h · cookie httpOnly
        </p>
      </div>
    </main>
  );
}
