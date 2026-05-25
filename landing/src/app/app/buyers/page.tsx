import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

interface BuyerRow {
  id: number;
  name: string;
  country: string | null;
  vat: string | null;
  contact: string | null;
  notes: string | null;
  created_at: string;
}

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Buyers — DFT' };

interface PageProps {
  searchParams: {
    q?: string;
    created?: string;
    deleted?: string;
    error?: string;
  };
}

export default async function BuyersPage({ searchParams }: PageProps) {
  const q = (searchParams.q ?? '').trim().toLowerCase();
  const showCreated = searchParams.created === '1';
  const showDeleted = searchParams.deleted === '1';
  const showError = searchParams.error;

  let rows: BuyerRow[] = [];
  let me: UserRead | null = null;
  let fetchError: string | null = null;

  try {
    [rows, me] = await Promise.all([
      apiGet<BuyerRow[]>('/byproduct/buyers'),
      apiGet<UserRead>('/auth/me'),
    ]);
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const role = me?.role;
  const canCreate = role === 'admin' || role === 'operator';

  const filtered = q
    ? rows.filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          (r.country ?? '').toLowerCase().includes(q) ||
          (r.vat ?? '').toLowerCase().includes(q),
      )
    : rows;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Master data
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">Buyers</h1>
          {canCreate && (
            <Link
              href="/app/buyers/new"
              className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
            >
              + New buyer
            </Link>
          )}
        </div>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {filtered.length} of {rows.length} buyers
          {q ? ` · search "${q}"` : ''}
        </p>
      </header>

      {showCreated && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Buyer created
        </p>
      )}
      {showDeleted && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Buyer deleted (soft)
        </p>
      )}
      {showError && (
        <p
          role="alert"
          className="mt-6 border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent"
        >
          {showError}
        </p>
      )}

      <section className="mt-6 flex flex-wrap items-end justify-end gap-4 border-b border-rule pb-6">
        <form
          method="GET"
          action="/app/buyers"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Search</span>
            <input
              type="search"
              name="q"
              defaultValue={q}
              placeholder="name, country, VAT"
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

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Name</Th>
              <Th>Country</Th>
              <Th>VAT</Th>
              <Th>Contact</Th>
              <Th>Notes</Th>
              <Th className="text-right">
                <span className="sr-only">Open</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && !fetchError && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-ink-mute">
                  No buyers match the filter.
                </td>
              </tr>
            )}
            {filtered.map((r) => (
              <tr
                key={r.id}
                className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
              >
                <Td className="text-ink">{r.name}</Td>
                <Td className="text-ink-soft">{r.country ?? '—'}</Td>
                <Td className="text-ink-soft">{r.vat ?? '—'}</Td>
                <Td className="text-ink-soft">{r.contact ?? '—'}</Td>
                <Td className="text-ink-mute max-w-[20rem] truncate" title={r.notes ?? ''}>
                  {r.notes ?? '—'}
                </Td>
                <Td className="text-right">
                  <Link
                    href={`/app/buyers/${r.id}`}
                    className="text-ink-soft hover:text-ink"
                    aria-label={`Open buyer ${r.name}`}
                  >
                    →
                  </Link>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
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
