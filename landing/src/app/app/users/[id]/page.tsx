import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deactivateUserAction, reactivateUserAction } from '@/lib/user-actions';

type User = components['schemas']['UserRead'];
type Role = 'admin' | 'operator' | 'viewer' | 'certifier';

const ROLE_LABEL: Record<Role, string> = {
  admin: 'Admin',
  operator: 'Operator',
  viewer: 'Viewer',
  certifier: 'Certifier',
};

const ROLE_PILL: Record<Role, string> = {
  admin: 'border-ink bg-ink/10 text-ink',
  operator: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
  viewer: 'border-rule bg-bg text-ink-soft',
  certifier: 'border-ink-mute bg-bg text-ink-mute',
};

export const dynamic = 'force-dynamic';
export const metadata = { title: 'User — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: {
    created?: string;
    updated?: string;
    deactivated?: string;
    reactivated?: string;
    error?: string;
  };
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-GB');
}

function asRole(v: string): Role {
  return (['admin', 'operator', 'viewer', 'certifier'] as const).includes(v as Role)
    ? (v as Role)
    : 'viewer';
}

export default async function UserDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let user: User | null = null;
  let me: User | null = null;
  let fetchError: string | null = null;

  try {
    [user, me] = await Promise.all([
      apiGet<User>(`/users/${id}`),
      apiGet<User>('/auth/me'),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    if (e instanceof ApiError && e.status === 403) {
      return (
        <div className="mx-auto max-w-editorial">
          <p className="border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent">
            Admin role required.
          </p>
        </div>
      );
    }
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            <Link href="/app/users" className="hover:text-ink">
              Users
            </Link>{' '}
            / #{id}
          </p>
          <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Not found</h1>
        </header>
        {fetchError && (
          <div className="mt-6 border border-accent bg-accent/5 p-4 font-mono text-[0.75rem] text-accent">
            {fetchError}
          </div>
        )}
      </div>
    );
  }

  const isAdmin = me?.role === 'admin';
  const isSelf = me?.id === user.id;
  const role = asRole(user.role);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/users" className="hover:text-ink">
            Users
          </Link>{' '}
          / {user.email}
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">
            {user.full_name ?? user.email}
            {!user.active && (
              <span className="ml-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent">
                · disabled
              </span>
            )}
            {isSelf && (
              <span className="ml-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
                · you
              </span>
            )}
          </h1>
          {isAdmin && (
            <div className="flex items-center gap-2">
              <Link
                href={`/app/users/${user.id}/edit`}
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Edit
              </Link>
              {!isSelf && user.active && (
                <form action={deactivateUserAction}>
                  <input type="hidden" name="id" value={user.id} />
                  <button
                    type="submit"
                    className="border border-accent px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent hover:bg-accent/10"
                  >
                    Deactivate
                  </button>
                </form>
              )}
              {!isSelf && !user.active && (
                <form action={reactivateUserAction}>
                  <input type="hidden" name="id" value={user.id} />
                  <button
                    type="submit"
                    className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
                  >
                    Reactivate
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
        <p className="mt-3 font-mono text-[0.72rem] text-ink-soft">
          <span
            className={`mr-2 inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${ROLE_PILL[role]}`}
          >
            {ROLE_LABEL[role]}
          </span>
          {user.email}
        </p>
      </header>

      {searchParams.created === '1' && <Banner kind="ok">User created</Banner>}
      {searchParams.updated === '1' && <Banner kind="ok">User updated</Banner>}
      {searchParams.deactivated === '1' && <Banner kind="ok">User deactivated</Banner>}
      {searchParams.reactivated === '1' && <Banner kind="ok">User reactivated</Banner>}
      {searchParams.error && <Banner kind="err">{searchParams.error}</Banner>}

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DataBlock title="Identity">
          <Row label="Email">{user.email}</Row>
          <Row label="Full name">{user.full_name ?? '—'}</Row>
        </DataBlock>

        <DataBlock title="Access">
          <Row label="Role">{ROLE_LABEL[role]}</Row>
          <Row label="Status">{user.active ? 'Active' : 'Disabled'}</Row>
        </DataBlock>

        <DataBlock title="Audit" full>
          <Row label="Created">{fmtDateTime(user.created_at)}</Row>
          <Row label="Updated">{fmtDateTime(user.updated_at)}</Row>
        </DataBlock>
      </section>
    </div>
  );
}

function Banner({ kind, children }: { kind: 'ok' | 'err'; children: React.ReactNode }) {
  const cls =
    kind === 'ok'
      ? 'border-olive-deep bg-olive-deep/5 text-olive-deep'
      : 'border-accent bg-accent/5 text-accent';
  return (
    <p
      role={kind === 'ok' ? 'status' : 'alert'}
      className={`mt-6 border ${cls} px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em]`}
    >
      {children}
    </p>
  );
}

function DataBlock({
  title,
  children,
  full,
}: {
  title: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <section className={`border border-rule bg-bg-soft p-5 ${full ? 'sm:col-span-2' : ''}`}>
      <h2 className="mb-3 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
        {title}
      </h2>
      <dl className="space-y-1.5">{children}</dl>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-rule/40 pb-1.5 last:border-b-0 last:pb-0">
      <dt className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
        {label}
      </dt>
      <dd className="font-mono text-[0.78rem] text-ink-soft text-right">{children}</dd>
    </div>
  );
}
