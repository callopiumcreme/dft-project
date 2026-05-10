import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { updateUserAction, type UserFormState } from '@/lib/user-actions';
import UserForm from '../../_components/user-form';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

interface PageProps {
  params: { id: string };
}

export default async function EditUserPage({ params }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let user: UserRead | null = null;
  let me: UserRead | null = null;

  try {
    [user, me] = await Promise.all([
      apiGet<UserRead>(`/users/${id}`),
      apiGet<UserRead>('/auth/me'),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    if (e instanceof ApiError && e.status === 404) notFound();
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
  if (!user) notFound();

  const userId = user.id;
  const isSelf = me.id === user.id;

  const boundAction = async (
    prev: UserFormState,
    fd: FormData,
  ): Promise<UserFormState> => {
    'use server';
    return updateUserAction(userId, prev, fd);
  };

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Admin ·{' '}
          <Link href="/app/users" className="hover:text-ink">
            Users
          </Link>{' '}
          /{' '}
          <Link href={`/app/users/${user.id}`} className="hover:text-ink">
            {user.email}
          </Link>
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Edit user</h1>
        {isSelf && (
          <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-mute">
            Editing your own account. Role and active flag are locked to prevent self-lockout.
          </p>
        )}
      </header>

      <UserForm
        action={boundAction}
        initial={user}
        mode="edit"
        isSelf={isSelf}
        submitLabel="Save changes"
        cancelHref={`/app/users/${user.id}`}
      />
    </div>
  );
}
