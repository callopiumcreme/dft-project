import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import {
  InputsTableClient,
  type InputsFilters,
  type SupplierLite,
} from './_components/inputs-table-client';

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
// Backend `/daily-inputs` caps limit at 10000 (see
// backend/app/routers/daily_inputs.py). When a filter is active we ask for
// the whole result set so the user sees the full range without paging.
const FILTERED_LIMIT = 10000;

export default async function InputsPage({ searchParams }: PageProps) {
  const date_from = (searchParams.date_from ?? '').trim();
  const date_to = (searchParams.date_to ?? '').trim();
  const supplier_id = (searchParams.supplier_id ?? '').trim();
  const showCreated = searchParams.created === '1';
  const showDeleted = searchParams.deleted === '1';
  const showError = searchParams.error;

  const hasFilter = Boolean(date_from || date_to || supplier_id);
  const effectiveLimit = hasFilter ? FILTERED_LIMIT : PAGE_SIZE;

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
          limit: effectiveLimit,
        },
      }),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  const filters: InputsFilters = {
    date_from: date_from || undefined,
    date_to: date_to || undefined,
    supplier_id: supplier_id || undefined,
  };
  const supplierLites: SupplierLite[] = suppliers.map((s) => ({
    id: s.id,
    code: s.code,
    name: s.name,
  }));
  const rangeLabel =
    date_from || date_to
      ? ` · range ${date_from || '…'} → ${date_to || '…'}`
      : ' · most recent';

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

      {!fetchError && (
        <InputsTableClient
          initialRows={rows}
          pageSize={PAGE_SIZE}
          filters={filters}
          suppliers={supplierLites}
          rangeLabel={rangeLabel}
          initialHasMore={!hasFilter && rows.length === PAGE_SIZE}
        />
      )}
    </div>
  );
}
