import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Row = components['schemas']['UserRead'];
type Role = 'admin' | 'operator' | 'viewer' | 'certifier';

const ROLES: Role[] = ['admin', 'operator', 'viewer', 'certifier'];

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
export const metadata = { title: 'Users — DFT' };

const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function asRole(v: string): Role {
  return (ROLES as readonly string[]).includes(v) ? (v as Role) : 'viewer';
}

function sanitizeRole(v: string | undefined): Role | undefined {
  return v && (ROLES as readonly string[]).includes(v) ? (v as Role) : undefined;
}

interface PageProps {
  searchParams: {
    role?: string;
    q?: string;
    active?: string;
    created?: string;
    updated?: string;
    deactivated?: string;
    reactivated?: string;
    error?: string;
  };
}

export default async function UsersPage({ searchParams }: PageProps) {
  const role = sanitizeRole(searchParams.role);
  const q = (searchParams.q ?? '').trim().toLowerCase();
  const showAll = searchParams.active === 'all';

  let me: Row | null = null;
  try {
    me = await apiGet<Row>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
  }

  if (!me || me.role !== 'admin') {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            Admin
          </p>
          <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Users</h1>
        </header>
        <p className="mt-6 border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent">
          Admin role required.
        </p>
      </div>
    );
  }

  let rows: Row[] = [];
  let fetchError: string | null = null;
  try {
    rows = await apiGet<Row[]>('/users', {
      query: {
        ...(showAll ? {} : { active_only: true }),
        ...(role ? { role } : {}),
      },
    });
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const filtered = q
    ? rows.filter(
        (r) =>
          r.email.toLowerCase().includes(q) ||
          (r.full_name ?? '').toLowerCase().includes(q),
      )
    : rows;

  const counts: Record<Role, number> = { admin: 0, operator: 0, viewer: 0, certifier: 0 };
  let activeCount = 0;
  let disabledCount = 0;
  for (const r of rows) {
    counts[asRole(r.role)]++;
    if (r.active) activeCount++;
    else disabledCount++;
  }

  const baseQuery = (extra: Record<string, string>) => {
    const params = new URLSearchParams();
    if (role) params.set('role', role);
    if (showAll) params.set('active', 'all');
    if (q) params.set('q', q);
    for (const [k, v] of Object.entries(extra)) {
      if (v === '') params.delete(k);
      else params.set(k, v);
    }
    const s = params.toString();
    return s ? `?${s}` : '';
  };

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">Admin</p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">Users</h1>
          <Link
            href="/app/users/new"
            className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
          >
            + New user
          </Link>
        </div>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {filtered.length} of {rows.length} users
          {showAll ? ' · all' : ' · active only'}
          {role ? ` · role = ${ROLE_LABEL[role]}` : ''}
          {q ? ` · search "${q}"` : ''}
        </p>
      </header>

      {searchParams.created === '1' && <Banner kind="ok">User created</Banner>}
      {searchParams.updated === '1' && <Banner kind="ok">User updated</Banner>}
      {searchParams.deactivated === '1' && <Banner kind="ok">User deactivated</Banner>}
      {searchParams.reactivated === '1' && <Banner kind="ok">User reactivated</Banner>}
      {searchParams.error && <Banner kind="err">{searchParams.error}</Banner>}

      <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <nav className="flex flex-wrap gap-1 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
          <Link
            href={`/app/users${baseQuery({ role: '' })}`}
            className={
              !role
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            All roles
          </Link>
          {ROLES.map((r) => (
            <Link
              key={r}
              href={`/app/users${baseQuery({ role: r })}`}
              className={
                role === r
                  ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                  : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
              }
            >
              {ROLE_LABEL[r]}
            </Link>
          ))}
          <span className="mx-2 self-center text-ink-mute">·</span>
          <Link
            href={`/app/users${baseQuery({ active: '' })}`}
            className={
              !showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            Active
          </Link>
          <Link
            href={`/app/users${baseQuery({ active: 'all' })}`}
            className={
              showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            All (with disabled)
          </Link>
        </nav>
        <form
          method="GET"
          action="/app/users"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          {role && <input type="hidden" name="role" value={role} />}
          {showAll && <input type="hidden" name="active" value="all" />}
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Search</span>
            <input
              type="search"
              name="q"
              defaultValue={q}
              placeholder="email, name"
              className="border border-rule bg-bg-soft px-2 py-1 text-ink lowercase tracking-normal w-56"
            />
          </label>
          <button
            type="submit"
            className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
          >
            Search
          </button>
        </form>
      </section>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      <section className="mt-6 grid grid-cols-2 sm:grid-cols-6 gap-3">
        <KpiTile label="Total" value={String(rows.length)} />
        <KpiTile label="Active" value={String(activeCount)} />
        <KpiTile label="Disabled" value={String(disabledCount)} alert={disabledCount > 0} />
        <KpiTile label="Admins" value={String(counts.admin)} />
        <KpiTile label="Operators" value={String(counts.operator)} />
        <KpiTile label="Viewers" value={String(counts.viewer)} />
      </section>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Email</Th>
              <Th>Name</Th>
              <Th>Role</Th>
              <Th>Status</Th>
              <Th>Created</Th>
              <Th className="text-right">
                <span className="sr-only">Open</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && !fetchError && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-ink-mute">
                  No users match the filter.
                </td>
              </tr>
            )}
            {filtered.map((r) => {
              const rRole = asRole(r.role);
              const isMe = me!.id === r.id;
              return (
                <tr
                  key={r.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink">
                    {r.email}
                    {isMe && (
                      <span className="ml-2 text-[0.6rem] uppercase tracking-[0.14em] text-ink-mute">
                        · you
                      </span>
                    )}
                  </Td>
                  <Td className="text-ink-soft">{r.full_name ?? '—'}</Td>
                  <Td>
                    <span
                      className={`inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${ROLE_PILL[rRole]}`}
                    >
                      {ROLE_LABEL[rRole]}
                    </span>
                  </Td>
                  <Td>
                    {r.active ? (
                      <span className="text-olive-deep">Active</span>
                    ) : (
                      <span className="inline-block border border-accent bg-accent/5 px-2 py-0.5 text-[0.65rem] uppercase text-accent">
                        Disabled
                      </span>
                    )}
                  </Td>
                  <Td className="text-ink-soft">{fmtDate(r.created_at)}</Td>
                  <Td className="text-right">
                    <Link
                      href={`/app/users/${r.id}`}
                      className="text-ink-soft hover:text-ink"
                      aria-label={`Open user ${r.email}`}
                    >
                      →
                    </Link>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
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

function KpiTile({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <div className="border border-rule bg-bg-soft p-4">
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">{label}</p>
      <p
        className={`mt-2 font-display text-2xl tracking-editorial ${
          alert ? 'text-accent' : 'text-ink'
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-normal ${className}`}>{children}</th>;
}

function Td({
  className = '',
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
