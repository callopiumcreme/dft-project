import Link from 'next/link';
import { ApiError } from '@/lib/api';
import {
  getWarehouseStock,
  getWarehouseMovements,
  type ProductKind,
  type WarehouseStockRow,
  type WarehouseMovement,
} from '@/lib/warehouse-client';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Warehouse — DFT' };

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

const STOCKABLE = ['eu_oil', 'plus_oil', 'carbon_black', 'metal_scrap'] as const;
const FLOW_THROUGH = ['syngas', 'h2o'] as const;
type StockableKind = (typeof STOCKABLE)[number];
type FlowThroughKind = (typeof FLOW_THROUGH)[number];

const STOCKABLE_LABEL: Record<(typeof STOCKABLE)[number], string> = {
  eu_oil: 'Pyrolysis oil EU (DEV-P100)',
  plus_oil: 'Pyrolysis oil PLUS (DEV-P200)',
  carbon_black: 'Carbon black',
  metal_scrap: 'Metal scrap',
};

const FLOW_THROUGH_LABEL: Record<(typeof FLOW_THROUGH)[number], string> = {
  syngas: 'Syngas (pyrolysis self-consumption)',
  h2o: 'H₂O (vented as steam)',
};

const PRODUCT_LABEL: Record<ProductKind, string> = {
  eu_oil: 'EU oil',
  plus_oil: 'Plus oil',
  carbon_black: 'Carbon black',
  metal_scrap: 'Metal scrap',
  syngas: 'Syngas',
  h2o: 'H₂O',
};

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${numFmt.format(n)} kg`;
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function emptyStock(kind: ProductKind): WarehouseStockRow {
  return {
    product_kind: kind,
    stock_kg: '0',
    produced_total_kg: '0',
    dispatched_total_kg: '0',
    produced_ytd_kg: '0',
    opening_balance_kg: '0',
    reserved_kg: '0',
    pos_issued_kg: '0',
    pos_issued_by_year: {},
    at_utb_awaiting_pos_kg: '0',
    last_movement_at: null,
  };
}

function sanitizeProductKind(v: string | undefined): ProductKind | undefined {
  if (!v) return undefined;
  const all: ProductKind[] = [...STOCKABLE, ...FLOW_THROUGH];
  return (all as string[]).includes(v) ? (v as ProductKind) : undefined;
}

interface PageProps {
  searchParams: {
    product_kind?: string;
  };
}

export default async function WarehousePage({ searchParams }: PageProps) {
  const productFilter = sanitizeProductKind(searchParams.product_kind);

  let stockRows: WarehouseStockRow[] = [];
  let movements: WarehouseMovement[] = [];
  let fetchError: string | null = null;

  try {
    const [stock, movs] = await Promise.all([
      getWarehouseStock(),
      getWarehouseMovements({ limit: 50, product_kind: productFilter }),
    ]);
    stockRows = stock;
    movements = movs;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const stockByKind = new Map<ProductKind, WarehouseStockRow>();
  for (const r of stockRows) stockByKind.set(r.product_kind, r);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Operations
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Warehouse
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Real-time stock per product
        </p>
      </header>

      {fetchError && (
        <div className="mt-6 border border-accent bg-accent/5 p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      {/* Section B — Stockable products */}
      <section className="mt-6">
        <p className="mb-3 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Stockable products
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {STOCKABLE.map((kind) => {
            const row = stockByKind.get(kind) ?? emptyStock(kind);
            const isEuOil = kind === 'eu_oil';
            return (
              <div key={kind} className="border border-rule bg-bg-soft p-4">
                <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
                  {STOCKABLE_LABEL[kind]}
                </p>
                <p className="mt-2 font-display text-2xl tracking-editorial text-ink tabular-nums">
                  {fmtKg(row.stock_kg)}
                </p>
                <dl className="mt-3 space-y-1 font-mono text-[0.7rem]">
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-mute">Available</dt>
                    <dd className="tabular-nums text-ink">{fmtKg(row.stock_kg)}</dd>
                  </div>
                  {isEuOil && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink-mute">POS issued 2025</dt>
                      <dd className="tabular-nums text-ink-soft">
                        {fmtKg(row.pos_issued_by_year?.['2025'] ?? '0')}
                      </dd>
                    </div>
                  )}
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-mute">Produced YTD</dt>
                    <dd className="tabular-nums text-ink-soft">{fmtKg(row.produced_ytd_kg)}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-mute">Opening balance</dt>
                    <dd className="tabular-nums text-ink-soft">{fmtKg(row.opening_balance_kg)}</dd>
                  </div>
                  {isEuOil && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink-mute">POS issued 2024</dt>
                      <dd className="tabular-nums text-ink-soft">
                        {fmtKg(row.pos_issued_by_year?.['2024'] ?? '0')}
                      </dd>
                    </div>
                  )}
                  {!isEuOil && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-ink-mute">Dispatched YTD</dt>
                      <dd className="tabular-nums text-ink-soft">{fmtKg(row.dispatched_total_kg)}</dd>
                    </div>
                  )}
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-mute">Last movement</dt>
                    <dd className="tabular-nums text-ink-soft">{fmtDate(row.last_movement_at)}</dd>
                  </div>
                </dl>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section C — Flow-through (not stocked) */}
      <section className="mt-8">
        <p className="mb-3 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Flow-through (not stocked)
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FLOW_THROUGH.map((kind) => {
            const row = stockByKind.get(kind) ?? emptyStock(kind);
            return (
              <div key={kind} className="border border-rule bg-bg-soft p-4">
                <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
                  {FLOW_THROUGH_LABEL[kind]}
                </p>
                <p className="mt-2 font-display text-2xl tracking-editorial text-ink tabular-nums">
                  {fmtKg(row.produced_total_kg)}
                  <span className="ml-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
                    prodotti YTD
                  </span>
                </p>
                <dl className="mt-3 space-y-1 font-mono text-[0.7rem]">
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-mute">Dispersed YTD</dt>
                    <dd className="tabular-nums text-ink-soft">{fmtKg(row.dispatched_total_kg)}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ink-mute">Net balance</dt>
                    <dd className="tabular-nums text-ink-soft">
                      {fmtKg(row.stock_kg)}
                      <span className="ml-1 text-[0.62rem] text-ink-mute">(always 0)</span>
                    </dd>
                  </div>
                </dl>
              </div>
            );
          })}
        </div>
      </section>

      {/* Section D — Recent movements */}
      <section className="mt-8">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-rule pb-3">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            Recent movements
          </p>
          <form
            method="GET"
            action="/app/warehouse"
            className="flex flex-wrap items-end gap-2 font-mono text-[0.68rem] uppercase tracking-[0.12em]"
          >
            <label className="flex items-center gap-2">
              <span className="text-ink-mute">Product</span>
              <select
                name="product_kind"
                defaultValue={productFilter ?? ''}
                className="border border-rule bg-bg-soft px-2 py-1 text-ink"
              >
                <option value="">— all —</option>
                {[...STOCKABLE, ...FLOW_THROUGH].map((k) => (
                  <option key={k} value={k}>
                    {PRODUCT_LABEL[k]}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="submit"
              className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
            >
              Filter
            </button>
            {productFilter && (
              <Link
                href="/app/warehouse"
                className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
              >
                Reset
              </Link>
            )}
          </form>
        </div>

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
              {movements.length === 0 && !fetchError && (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-ink-mute">
                    No movements logged.
                  </td>
                </tr>
              )}
              {movements.map((m) => (
                <tr
                  key={m.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink">{fmtDate(m.event_date)}</Td>
                  <Td className="text-ink-soft">{m.event_type}</Td>
                  <Td className="text-ink-soft">{PRODUCT_LABEL[m.product_kind] ?? m.product_kind}</Td>
                  <Td className="text-right tabular-nums text-ink-soft">{fmtKg(m.kg_in)}</Td>
                  <Td className="text-right tabular-nums text-ink-soft">{fmtKg(m.kg_out)}</Td>
                  <Td className="text-right tabular-nums text-ink font-medium">
                    {fmtKg(m.post_balance_kg)}
                  </Td>
                  <Td className="text-ink-soft">{m.ref_doc_no ?? '—'}</Td>
                  <Td className="text-ink-mute" title={m.notes ?? undefined}>
                    {m.notes ?? '—'}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {movements.length === 50 && (
          <p className="mt-3 font-mono text-[0.7rem] uppercase tracking-[0.12em] text-ink-mute">
            Showing last 50 movements. Filter by product to narrow further.
          </p>
        )}
      </section>
    </div>
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
