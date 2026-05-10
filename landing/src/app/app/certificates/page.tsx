import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Row = components['schemas']['CertificateRead'];
type UserRead = components['schemas']['UserRead'];
type Status = 'active' | 'expired' | 'revoked' | 'placeholder';

const STATUSES: Status[] = ['active', 'expired', 'revoked', 'placeholder'];

const STATUS_LABEL: Record<Status, string> = {
  active: 'Active',
  expired: 'Expired',
  revoked: 'Revoked',
  placeholder: 'Placeholder',
};

const STATUS_PILL: Record<Status, string> = {
  active: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
  expired: 'border-accent bg-bg text-accent',
  revoked: 'border-ink-mute bg-bg text-ink-mute',
  placeholder: 'border-rule bg-bg text-ink-soft',
};

export const dynamic = 'force-dynamic';

const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function sanitizeStatus(v: string | undefined): Status | undefined {
  return v && (STATUSES as string[]).includes(v) ? (v as Status) : undefined;
}

interface PageProps {
  searchParams: {
    status?: string;
    q?: string;
    active?: string;
    created?: string;
    deleted?: string;
    error?: string;
  };
}

export default async function CertificatesPage({ searchParams }: PageProps) {
  const status = sanitizeStatus(searchParams.status);
  const q = (searchParams.q ?? '').trim().toLowerCase();
  const showAll = searchParams.active === 'all';
  const showCreated = searchParams.created === '1';
  const showDeleted = searchParams.deleted === '1';
  const showError = searchParams.error;

  let rows: Row[] = [];
  let me: UserRead | null = null;
  let fetchError: string | null = null;

  try {
    const [certsRes, meRes] = await Promise.all([
      apiGet<Row[]>('/certificates', {
        query: {
          ...(status ? { status } : {}),
          ...(showAll ? { include_deleted: true } : {}),
        },
      }),
      apiGet<UserRead>('/auth/me'),
    ]);
    rows = certsRes;
    me = meRes;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const isAdmin = me?.role === 'admin';

  const filtered = q
    ? rows.filter(
        (r) =>
          r.cert_number.toLowerCase().includes(q) ||
          r.scheme.toLowerCase().includes(q) ||
          (r.notes ?? '').toLowerCase().includes(q),
      )
    : rows;

  const counts: Record<Status, number> = {
    active: 0,
    expired: 0,
    revoked: 0,
    placeholder: 0,
  };
  for (const r of rows) {
    if ((STATUSES as string[]).includes(r.status)) counts[r.status as Status]++;
  }

  const today = new Date();
  const expiringSoon = rows.filter((r) => {
    if (!r.expires_at || r.status !== 'active' || r.deleted_at) return false;
    const exp = new Date(r.expires_at);
    if (!Number.isFinite(exp.getTime())) return false;
    const days = (exp.getTime() - today.getTime()) / (1000 * 60 * 60 * 24);
    return days >= 0 && days <= 60;
  }).length;

  const baseQuery = (extra: Record<string, string>) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
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
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Master data
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">Certificates</h1>
          {isAdmin && (
            <Link
              href="/app/certificates/new"
              className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
            >
              + New certificate
            </Link>
          )}
        </div>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {filtered.length} of {rows.length} certificates
          {showAll ? ' · deleted included' : ' · active only'}
          {status ? ` · status = ${STATUS_LABEL[status]}` : ''}
          {q ? ` · search "${q}"` : ''}
        </p>
      </header>

      {showCreated && <Banner kind="ok">Certificate created</Banner>}
      {showDeleted && <Banner kind="ok">Certificate deleted (soft)</Banner>}
      {showError && <Banner kind="err">{showError}</Banner>}

      <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <nav className="flex flex-wrap gap-1 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
          <Link
            href={`/app/certificates${baseQuery({ status: '', active: showAll ? 'all' : '' })}`}
            className={
              !status
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            All
          </Link>
          {STATUSES.map((s) => (
            <Link
              key={s}
              href={`/app/certificates${baseQuery({ status: s, active: showAll ? 'all' : '' })}`}
              className={
                status === s
                  ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                  : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
              }
            >
              {STATUS_LABEL[s]}
            </Link>
          ))}
          <span className="mx-2 self-center text-ink-mute">·</span>
          <Link
            href={`/app/certificates${baseQuery({ active: '' })}`}
            className={
              !showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            Active
          </Link>
          <Link
            href={`/app/certificates${baseQuery({ active: 'all' })}`}
            className={
              showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            All (with deleted)
          </Link>
        </nav>
        <form
          method="GET"
          action="/app/certificates"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          {status && <input type="hidden" name="status" value={status} />}
          {showAll && <input type="hidden" name="active" value="all" />}
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Search</span>
            <input
              type="search"
              name="q"
              defaultValue={q}
              placeholder="number, scheme, notes"
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

      <section className="mt-6 grid grid-cols-2 sm:grid-cols-5 gap-3">
        <KpiTile label="Total" value={String(rows.length)} />
        <KpiTile label="Active" value={String(counts.active)} />
        <KpiTile label="Expired" value={String(counts.expired)} />
        <KpiTile label="Placeholder" value={String(counts.placeholder)} />
        <KpiTile
          label="Expiring ≤60d"
          value={String(expiringSoon)}
          alert={expiringSoon > 0}
        />
      </section>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Number</Th>
              <Th>Scheme</Th>
              <Th>Status</Th>
              <Th>Issued</Th>
              <Th>Expires</Th>
              <Th>Suppliers</Th>
              <Th>Notes</Th>
              <Th className="text-right">
                <span className="sr-only">Open</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && !fetchError && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-ink-mute">
                  No certificates match the filter.
                </td>
              </tr>
            )}
            {filtered.map((r) => {
              const s = (STATUSES as string[]).includes(r.status)
                ? (r.status as Status)
                : 'placeholder';
              const deleted = !!r.deleted_at;
              return (
                <tr
                  key={r.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink">{r.cert_number}</Td>
                  <Td className="text-ink-soft">{r.scheme}</Td>
                  <Td>
                    <span
                      className={`inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${STATUS_PILL[s]}`}
                    >
                      {STATUS_LABEL[s]}
                    </span>
                    {deleted && (
                      <span className="ml-1 inline-block border border-accent bg-accent/5 px-2 py-0.5 text-[0.65rem] uppercase text-accent">
                        deleted
                      </span>
                    )}
                  </Td>
                  <Td className="text-ink-soft">{fmtDate(r.issued_at)}</Td>
                  <Td className="text-ink-soft">{fmtDate(r.expires_at)}</Td>
                  <Td className="text-ink-soft tabular-nums">{r.supplier_ids.length}</Td>
                  <Td className="text-ink-mute max-w-[16rem] truncate" title={r.notes ?? ''}>
                    {r.notes ?? '—'}
                  </Td>
                  <Td className="text-right">
                    <Link
                      href={`/app/certificates/${r.id}`}
                      className="text-ink-soft hover:text-ink"
                      aria-label={`Open certificate ${r.cert_number}`}
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
  title,
}: {
  className?: string;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <td className={`px-3 py-2 ${className}`} title={title}>
      {children}
    </td>
  );
}
