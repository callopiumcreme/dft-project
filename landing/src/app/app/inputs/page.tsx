import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Input = components['schemas']['DailyInputRead'];
type Supplier = components['schemas']['SupplierRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Inputs — DFT' };

interface PageProps {
  searchParams: {
    date_from?: string;
    date_to?: string;
    supplier_id?: string;
    created?: string;
    deleted?: string;
    error?: string;
  };
}

const PAGE_SIZE = 50;

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(n);
}

export default async function InputsPage({ searchParams }: PageProps) {
  const date_from = (searchParams.date_from ?? '').trim();
  const date_to = (searchParams.date_to ?? '').trim();
  const supplier_id = (searchParams.supplier_id ?? '').trim();
  const showCreated = searchParams.created === '1';
  const showDeleted = searchParams.deleted === '1';
  const showError = searchParams.error;

  let rows: Input[] = [];
  let suppliers: Supplier[] = [];
  let fetchError: string | null = null;

  try {
    [rows, suppliers] = await Promise.all([
      apiGet<Input[]>('/daily-inputs', {
        query: {
          date_from: date_from || undefined,
          date_to: date_to || undefined,
          supplier_id: supplier_id ? Number(supplier_id) : undefined,
          limit: PAGE_SIZE,
        },
      }),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  const supplierMap = new Map(suppliers.map((s) => [s.id, s]));

  const totalKg = rows.reduce((sum, r) => sum + Number(r.total_input_kg ?? 0), 0);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Operations
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">Daily inputs</h1>
          <Link
            href="/app/inputs/new"
            className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
          >
            + New input
          </Link>
        </div>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {rows.length} entries · {fmtKg(totalKg)} kg total
          {date_from || date_to
            ? ` · range ${date_from || '…'} → ${date_to || '…'}`
            : ' · most recent'}
        </p>
      </header>

      {showCreated && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Input saved successfully
        </p>
      )}
      {showDeleted && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Input deleted (soft)
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

      <section className="mt-6 border-b border-rule pb-6">
        <form
          method="GET"
          action="/app/inputs"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">From</span>
            <input
              type="date"
              name="date_from"
              defaultValue={date_from}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">To</span>
            <input
              type="date"
              name="date_to"
              defaultValue={date_to}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Supplier</span>
            <select
              name="supplier_id"
              defaultValue={supplier_id}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink lowercase tracking-normal"
            >
              <option value="">All</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} · {s.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
          >
            Apply
          </button>
          <Link
            href="/app/inputs"
            className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
          >
            Reset
          </Link>
        </form>
      </section>

      {fetchError && (
        <div className="mt-6 border border-accent bg-accent/5 p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Date</Th>
              <Th>Time</Th>
              <Th>Supplier</Th>
              <Th>eRSV</Th>
              <Th className="text-right">Car</Th>
              <Th className="text-right">Truck</Th>
              <Th className="text-right">Special</Th>
              <Th className="text-right">Total kg</Th>
              <Th className="text-right">
                <span className="sr-only">Open</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !fetchError && (
              <tr>
                <td colSpan={9} className="px-3 py-6 text-center text-ink-mute">
                  No inputs match the filter.
                </td>
              </tr>
            )}
            {rows.map((r) => {
              const sup = supplierMap.get(r.supplier_id);
              return (
                <tr
                  key={r.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink">{r.entry_date}</Td>
                  <Td className="text-ink-mute">{r.entry_time ?? '—'}</Td>
                  <Td className="text-ink-soft">
                    {sup ? `${sup.code} · ${sup.name}` : `#${r.supplier_id}`}
                  </Td>
                  <Td className="text-ink-mute">{r.ersv_number ?? '—'}</Td>
                  <Td className="text-right text-ink-soft">{fmtKg(r.car_kg)}</Td>
                  <Td className="text-right text-ink-soft">{fmtKg(r.truck_kg)}</Td>
                  <Td className="text-right text-ink-soft">{fmtKg(r.special_kg)}</Td>
                  <Td className="text-right text-ink font-medium">
                    {fmtKg(r.total_input_kg)}
                  </Td>
                  <Td className="text-right">
                    <Link
                      href={`/app/inputs/${r.id}`}
                      className="text-ink-soft hover:text-ink"
                      aria-label={`Open input ${r.id}`}
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

      {rows.length === PAGE_SIZE && (
        <p className="mt-3 font-mono text-[0.7rem] uppercase tracking-[0.12em] text-ink-mute">
          Showing first {PAGE_SIZE}. Narrow filter to see more.
        </p>
      )}
    </div>
  );
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-normal ${className}`}>{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
