import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import {
  ProductionTableClient,
  type ProductionFilters,
} from './_components/production-table-client';

type Production = components['schemas']['DailyProductionRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Daily production — DFT' };

interface PageProps {
  searchParams: {
    date_from?: string;
    date_to?: string;
    created?: string;
    updated?: string;
    deleted?: string;
    error?: string;
  };
}

const PAGE_SIZE = 50;
// Backend `/daily-production` caps limit at 1000 (see
// backend/app/routers/daily_production.py). When a date filter is active we
// ask for the whole range so the user sees everything without paging.
const FILTERED_LIMIT = 1000;

export default async function ProductionPage({ searchParams }: PageProps) {
  const date_from = (searchParams.date_from ?? '').trim();
  const date_to = (searchParams.date_to ?? '').trim();
  const showCreated = searchParams.created === '1';
  const showDeleted = searchParams.deleted === '1';
  const showError = searchParams.error;

  const hasFilter = Boolean(date_from || date_to);
  const effectiveLimit = hasFilter ? FILTERED_LIMIT : PAGE_SIZE;

  let rows: Production[] = [];
  let fetchError: string | null = null;

  try {
    rows = await apiGet<Production[]>('/daily-production', {
      query: {
        date_from: date_from || undefined,
        date_to: date_to || undefined,
        limit: effectiveLimit,
      },
    });
  } catch (e) {
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  const filters: ProductionFilters = {
    date_from: date_from || undefined,
    date_to: date_to || undefined,
  };
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
          <h1 className="font-display text-4xl tracking-editorial text-ink">Daily production</h1>
          <Link
            href="/app/production/new"
            className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
          >
            + New day
          </Link>
        </div>
      </header>

      {showCreated && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Production day saved
        </p>
      )}
      {showDeleted && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Production day deleted (soft)
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
          action="/app/production"
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
          <button
            type="submit"
            className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
          >
            Apply
          </button>
          <Link
            href="/app/production"
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
        <ProductionTableClient
          initialRows={rows}
          pageSize={PAGE_SIZE}
          filters={filters}
          rangeLabel={rangeLabel}
          initialHasMore={!hasFilter && rows.length === PAGE_SIZE}
        />
      )}
    </div>
  );
}
