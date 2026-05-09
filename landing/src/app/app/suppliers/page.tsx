import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Row = components['schemas']['SupplierRead'];

export const dynamic = 'force-dynamic';

interface PageProps {
  searchParams: { active?: string; q?: string };
}

export default async function SuppliersPage({ searchParams }: PageProps) {
  const showAll = searchParams.active === 'all';
  const q = (searchParams.q ?? '').trim().toLowerCase();

  let rows: Row[] = [];
  let fetchError: string | null = null;

  try {
    rows = await apiGet<Row[]>('/suppliers', {
      query: { active_only: !showAll },
    });
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const filtered = q
    ? rows.filter(
        (r) =>
          r.code.toLowerCase().includes(q) ||
          r.name.toLowerCase().includes(q) ||
          (r.country ?? '').toLowerCase().includes(q),
      )
    : rows;

  const activeCount = rows.filter((r) => r.active).length;
  const aggregateCount = rows.filter((r) => r.is_aggregate).length;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Master data
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Suppliers</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {filtered.length} of {rows.length} suppliers
          {showAll ? ' · inactive included' : ' · active only'}
          {q ? ` · search "${q}"` : ''}
        </p>
      </header>

      <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <nav className="flex gap-1 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
          <Link
            href="/app/suppliers"
            className={
              !showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            Active
          </Link>
          <Link
            href="/app/suppliers?active=all"
            className={
              showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            All
          </Link>
        </nav>
        <form
          method="GET"
          action="/app/suppliers"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          {showAll && <input type="hidden" name="active" value="all" />}
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Search</span>
            <input
              type="search"
              name="q"
              defaultValue={q}
              placeholder="code, name, country"
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

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiTile label="Suppliers" value={String(rows.length)} />
        <KpiTile label="Active" value={String(activeCount)} />
        <KpiTile label="Aggregates" value={String(aggregateCount)} />
      </section>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Code</Th>
              <Th>Name</Th>
              <Th>Country</Th>
              <Th>Type</Th>
              <Th>Status</Th>
              <Th>Notes</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && !fetchError && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-ink-mute">
                  No suppliers match the filter.
                </td>
              </tr>
            )}
            {filtered.map((r) => (
              <tr
                key={r.id}
                className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
              >
                <Td className="text-ink">{r.code}</Td>
                <Td className="text-ink-soft">{r.name}</Td>
                <Td className="text-ink-soft">{r.country ?? '—'}</Td>
                <Td>
                  <span className="text-ink-soft">
                    {r.is_aggregate ? 'aggregate' : 'single'}
                  </span>
                </Td>
                <Td>
                  <Pill ok={r.active}>{r.active ? 'active' : 'inactive'}</Pill>
                </Td>
                <Td className="text-ink-mute max-w-[20rem] truncate" title={r.notes ?? ''}>
                  {r.notes ?? '—'}
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function KpiTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-rule bg-bg-soft p-4">
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">{label}</p>
      <p className="mt-2 font-display text-2xl tracking-editorial text-ink">{value}</p>
    </div>
  );
}

function Pill({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  const cls = ok
    ? 'border-olive-deep bg-olive-deep/10 text-olive-deep'
    : 'border-ink-mute bg-bg text-ink-mute';
  return (
    <span className={`inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${cls}`}>
      {children}
    </span>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 font-normal">{children}</th>;
}
function Td({ className = '', children, title }: { className?: string; children: React.ReactNode; title?: string }) {
  return <td className={`px-3 py-2 ${className}`} title={title}>{children}</td>;
}
