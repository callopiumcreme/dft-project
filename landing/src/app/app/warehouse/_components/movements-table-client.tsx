'use client';

import { useState } from 'react';

type ProductKind = 'eu_oil' | 'plus_oil' | 'carbon_black' | 'metal_scrap' | 'syngas' | 'h2o';

export interface WarehouseMovement {
  id: number;
  event_date: string;
  event_type: string;
  product_kind: ProductKind;
  kg_in: string;
  kg_out: string;
  post_balance_kg: string | null;
  ref_doc_no: string | null;
  consignment_id: number | null;
  notes: string | null;
}

interface Props {
  initialRows: WarehouseMovement[];
  pageSize: number;
  productFilter?: ProductKind;
  initialHasMore: boolean;
}

// Volume-weighted density (Σkg / Σlitres) from the 2025 kg→litres
// reconciliation bundle. Only the two oils have a meaningful litre value.
const DENSITY_KG_PER_L: Partial<Record<ProductKind, number>> = {
  eu_oil: 0.77082,
  plus_oil: 0.86161,
};

const PRODUCT_LABEL: Record<ProductKind, string> = {
  eu_oil: 'EU oil (DEV-P100)',
  plus_oil: 'Plus oil (DEV-P200)',
  carbon_black: 'Carbon black',
  metal_scrap: 'Metal scrap',
  syngas: 'Syngas',
  h2o: 'H₂O',
};

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${numFmt.format(n)} kg`;
}

function fmtLitres(v: string | null | undefined, densityKgPerL: number): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${numFmt.format(n / densityKgPerL)} L`;
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

export function MovementsTableClient({
  initialRows,
  pageSize,
  productFilter,
  initialHasMore,
}: Props) {
  const [rows, setRows] = useState<WarehouseMovement[]>(initialRows);
  const [hasMore, setHasMore] = useState<boolean>(initialHasMore);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadMore() {
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      qs.set('limit', String(pageSize));
      qs.set('offset', String(rows.length));
      if (productFilter) qs.set('product_kind', productFilter);

      const res = await fetch(`/api/warehouse/movements?${qs.toString()}`, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const more = (await res.json()) as WarehouseMovement[];
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
      <div className="mt-4 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Date</Th>
              <Th>Event</Th>
              <Th>Product</Th>
              <Th className="text-right">In (kg)</Th>
              <Th className="text-right">Out (kg)</Th>
              <Th className="text-right">Balance</Th>
              <Th>Doc</Th>
              <Th>Notes</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-ink-mute">
                  No movements logged.
                </td>
              </tr>
            )}
            {rows.map((m) => {
              const density = DENSITY_KG_PER_L[m.product_kind];
              return (
                <tr
                  key={m.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink">{fmtDate(m.event_date)}</Td>
                  <Td className="text-ink-soft">{m.event_type}</Td>
                  <Td className="text-ink-soft">{PRODUCT_LABEL[m.product_kind] ?? m.product_kind}</Td>
                  <Td className="text-right tabular-nums text-ink-soft">
                    {fmtKg(m.kg_in)}
                    {density !== undefined && Number(m.kg_in) > 0 && (
                      <span className="block text-[0.62rem] text-ink-mute">
                        ≈ {fmtLitres(m.kg_in, density)}
                      </span>
                    )}
                  </Td>
                  <Td className="text-right tabular-nums text-ink-soft">
                    {fmtKg(m.kg_out)}
                    {density !== undefined && Number(m.kg_out) > 0 && (
                      <span className="block text-[0.62rem] text-ink-mute">
                        ≈ {fmtLitres(m.kg_out, density)}
                      </span>
                    )}
                  </Td>
                  <Td className="text-right tabular-nums text-ink font-medium">
                    {fmtKg(m.post_balance_kg)}
                    {density !== undefined && m.post_balance_kg !== null && (
                      <span className="block text-[0.62rem] font-normal text-ink-mute">
                        ≈ {fmtLitres(m.post_balance_kg, density)}
                      </span>
                    )}
                  </Td>
                  <Td className="text-ink-soft">{m.ref_doc_no ?? '—'}</Td>
                  <Td className="text-ink-mute" title={m.notes ?? undefined}>
                    {m.notes ?? '—'}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

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
        {error && <span className="font-mono text-[0.7rem] text-accent">{error}</span>}
      </div>
    </>
  );
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-normal ${className}`}>{children}</th>;
}

function Td({
  children,
  className = '',
  title,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <td className={`px-3 py-2 ${className}`} title={title}>
      {children}
    </td>
  );
}
