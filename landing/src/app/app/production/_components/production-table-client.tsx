'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import type { components } from '@/lib/backend-types';

type Production = components['schemas']['DailyProductionRead'];

export interface ProductionFilters {
  date_from?: string;
  date_to?: string;
}

interface Props {
  initialRows: Production[];
  pageSize: number;
  filters: ProductionFilters;
  rangeLabel: string;
  // When a date filter is active the SSR call uses a high limit and
  // returns the full result set; the client should never offer "Show
  // more" in that mode. Caller forces initialHasMore=false.
  initialHasMore: boolean;
}

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(n);
}

export function ProductionTableClient({
  initialRows,
  pageSize,
  filters,
  rangeLabel,
  initialHasMore,
}: Props) {
  const [rows, setRows] = useState<Production[]>(initialRows);
  const [hasMore, setHasMore] = useState<boolean>(initialHasMore);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totals = useMemo(() => {
    let kgIn = 0;
    let euOut = 0;
    for (const r of rows) {
      kgIn += Number(r.kg_to_production ?? 0);
      euOut += Number(r.output_eu_kg ?? 0);
    }
    return { kgIn, euOut };
  }, [rows]);

  async function loadMore() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (filters.date_from) qs.set('date_from', filters.date_from);
      if (filters.date_to) qs.set('date_to', filters.date_to);
      qs.set('limit', String(pageSize));
      qs.set('offset', String(rows.length));

      const res = await fetch(`/api/daily-production?${qs.toString()}`, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const more = (await res.json()) as Production[];
      setRows((prev) => [...prev, ...more]);
      if (more.length < pageSize) setHasMore(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
        {rows.length} days · {fmtKg(totals.kgIn)} kg input · {fmtKg(totals.euOut)} kg EU output
        {rangeLabel}
      </p>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Date</Th>
              <Th className="text-right">Input kg</Th>
              <Th className="text-right">EU prod</Th>
              <Th className="text-right">Plus</Th>
              <Th className="text-right">Output EU</Th>
              <Th>Contract</Th>
              <Th className="text-right">
                <span className="sr-only">Open</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-ink-mute">
                  No production days match the filter.
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-rule/60 last:border-b-0 hover:bg-bg">
                <Td className="text-ink">{r.prod_date}</Td>
                <Td className="text-right text-ink-soft">{fmtKg(r.kg_to_production)}</Td>
                <Td className="text-right text-ink-soft">{fmtKg(r.eu_prod_kg)}</Td>
                <Td className="text-right text-ink-soft">{fmtKg(r.plus_prod_kg)}</Td>
                <Td className="text-right text-ink font-medium">{fmtKg(r.output_eu_kg)}</Td>
                <Td className="text-ink-mute">{r.contract_ref ?? '—'}</Td>
                <Td className="text-right">
                  <Link
                    href={`/app/production/${r.id}`}
                    className="text-ink-soft hover:text-ink"
                    aria-label={`Open production day ${r.prod_date}`}
                  >
                    →
                  </Link>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        {hasMore && (
          <button
            type="button"
            onClick={loadMore}
            disabled={loading}
            className="border border-ink bg-bg-soft px-3 py-1.5 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink hover:bg-ink hover:text-bg disabled:opacity-50"
          >
            {loading ? 'Loading…' : `Show ${pageSize} more`}
          </button>
        )}
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.12em] text-ink-mute">
          {rows.length} row{rows.length === 1 ? '' : 's'} loaded
          {!hasMore && rows.length > 0 ? ' · all' : ''}
        </p>
        {error && (
          <span className="font-mono text-[0.7rem] text-accent">{error}</span>
        )}
      </div>
    </>
  );
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-normal ${className}`}>{children}</th>;
}

function Td({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
