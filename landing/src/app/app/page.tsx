import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { apiGet, ApiError, SESSION_COOKIE } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { LogoutButton } from './logout-button';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

export default async function AppHomePage() {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) redirect('/login');

  let user: UserRead;
  try {
    user = await apiGet<UserRead>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      redirect('/login');
    }
    throw e;
  }

  return (
    <main className="min-h-dvh bg-bg px-6 py-12">
      <div className="mx-auto max-w-editorial">
        <header className="flex items-start justify-between border-b border-rule pb-6">
          <div>
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
              Area protetta
            </p>
            <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
              {user.full_name ?? user.email}
            </h1>
            <p className="mt-2 font-mono text-[0.75rem] uppercase tracking-[0.14em] text-olive-deep">
              {user.role}
            </p>
          </div>
          <LogoutButton />
        </header>
        <section className="mt-12">
          <p className="font-mono text-[0.78rem] text-ink-mute max-w-reading">
            Stub area /app — Sprint 3 layout shell + dashboard arrivano
            prossime issue (S3-5..S3-10). Auth flow OK.
          </p>
        </section>
      </div>
    </main>
  );
}
