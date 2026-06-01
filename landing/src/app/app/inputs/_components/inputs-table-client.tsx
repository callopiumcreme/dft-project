'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import type { components } from '@/lib/backend-types';
import { DocIdLink } from '@/components/ersv';

type Input = components['schemas']['DailyInputRead'];

export interface DocIdRow {
  id: number;
  doc_id_hash: string;
}

export interface InputsFilters {
  date_from?: string;
  date_to?: string;
  supplier_id?: string;
}

export interface SupplierLite {
  id: number;
  code: string;
  name: string;
}

interface Props {
  initialRows: Input[];
  initialDocIds: DocIdRow[];
  pageSize: number;
  filters: InputsFilters;
  suppliers: SupplierLite[];
  rangeLabel: string;
  // When a date/supplier filter is active the SSR call uses a high limit
  // and returns the full result set; the client should never offer "Show
  // more" in that mode. Caller forces initialHasMore=false.
  initialHasMore: boolean;
}

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(n);
}

export function InputsTableClient({
  initialRows,
  initialDocIds,
  pageSize,
  filters,
  suppliers,
  rangeLabel,
  initialHasMore,
}: Props) {
  const [rows, setRows] = useState<Input[]>(initialRows);
  const [docIdMap, setDocIdMap] = useState<Map<number, string>>(
    () => new Map(initialDocIds.map((d) => [d.id, d.doc_id_hash])),
  );
  const [hasMore, setHasMore] = useState<boolean>(initialHasMore);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const supplierMap = useMemo(
    () => new Map(suppliers.map((s) => [s.id, s])),
    [suppliers],
  );

  const totalKg = useMemo(
    () => rows.reduce((sum, r) => sum + Number(r.total_input_kg ?? 0), 0),
    [rows],
  );

  async function loadMore() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (filters.date_from) qs.set('date_from', filters.date_from);
      if (filters.date_to) qs.set('date_to', filters.date_to);
      if (filters.supplier_id) qs.set('supplier_id', filters.supplier_id);
      qs.set('limit', String(pageSize));
      qs.set('offset', String(rows.length));

      const res = await fetch(`/api/daily-inputs?${qs.toString()}`, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const more = (await res.json()) as Input[];
      setRows((prev) => [...prev, ...more]);
      if (more.length < pageSize) setHasMore(false);

      // Pull Doc IDs for the newly loaded rows so the column stays populated
      // past the first page (same batch endpoint as the SSR initial load).
      const newErsvIds = more.filter((r) => r.ersv_number).map((r) => r.id);
      if (newErsvIds.length > 0) {
        try {
          const dRes = await fetch(
            `/api/daily-inputs/doc-id-batch?ids=${newErsvIds.join(',')}`,
            { credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } },
          );
          if (dRes.ok) {
            const dRows = (await dRes.json()) as DocIdRow[];
            setDocIdMap((prev) => {
              const next = new Map(prev);
              for (const d of dRows) next.set(d.id, d.doc_id_hash);
              return next;
            });
          }
        } catch {
          // Doc IDs are advisory; a failed batch leaves '—' in the column.
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
        {rows.length} entries · {fmtKg(totalKg)} kg total
        {rangeLabel}
      </p>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Date</Th>
              <Th>Time</Th>
              <Th>Supplier</Th>
              <Th>Doc ID</Th>
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
            {rows.length === 0 && (
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
                  <Td className="text-ink-soft">
                    {r.ersv_number && docIdMap.get(r.id) ? (
                      <DocIdLink
                        docIdHash={docIdMap.get(r.id) as string}
                        ersvNumber={r.ersv_number}
                        dailyInputId={r.id}
                      />
                    ) : (
                      '—'
                    )}
                  </Td>
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
