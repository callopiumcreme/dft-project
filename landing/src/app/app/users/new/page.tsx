import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { createUserAction } from '@/lib/user-actions';
import UserForm from '../_components/user-form';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

export default async function NewUserPage() {
  let me: UserRead | null = null;
  try {
    me = await apiGet<UserRead>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
  }

  if (!me || me.role !== 'admin') {
    return (
      <div className="mx-auto max-w-editorial">
        <p className="border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent">
          Admin role required.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Admin ·{' '}
          <Link href="/app/users" className="hover:text-ink">
            Users
          </Link>
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">New user</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Create an account. Email is immutable after creation. Choose role carefully — admins can
          create and modify other users.
        </p>
      </header>

      <UserForm
        action={createUserAction}
        mode="create"
        submitLabel="Create user"
        cancelHref="/app/users"
      />
    </div>
  );
}
