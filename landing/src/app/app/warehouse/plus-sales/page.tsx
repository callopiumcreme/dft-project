import Link from 'next/link';
import { ApiError } from '@/lib/api';
import { getWarehouseStock, type WarehouseStockRow } from '@/lib/warehouse-client';
import { UmamiViewEvent } from '@/components/analytics/umami-view-event';

export const dynamic = 'force-dynamic';

const kgFmt = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return kgFmt.format(n);
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

export default async function PlusSalesPage() {
  let plusRow: WarehouseStockRow | null = null;
  let fetchError: string | null = null;

  try {
    const stock = await getWarehouseStock();
    plusRow = stock.find((r) => r.product_kind === 'plus_oil') ?? null;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  return (
    <div className="mx-auto max-w-editorial">
      <UmamiViewEvent name="view_plus_sales_placeholder" />

      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Warehouse
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Pyrolysis oil PLUS — Sales (Colombia)
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          PLUS oil (off-spec / domestic Colombia stream) sales tracking.
        </p>
      </header>

      <section className="mt-6 border border-rule bg-bg-soft p-5">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Status
        </p>
        <p className="mt-2 font-mono text-[0.85rem] text-ink">
          Awaiting sale documents from the Colombian buyer.
        </p>
        <p className="mt-2 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Schema is ready — sales will be recorded here as soon as invoices / PoS
          documents arrive from the buyer.
        </p>
      </section>

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiTile
          label="PLUS oil stock"
          value={`${fmtKg(plusRow?.stock_kg)} kg`}
        />
        <KpiTile
          label="Produced (cum.)"
          value={`${fmtKg(plusRow?.produced_total_kg)} kg`}
        />
        <KpiTile
          label="Last movement"
          value={fmtDate(plusRow?.last_movement_at)}
        />
      </section>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      <section className="mt-8 border-t border-rule pt-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
          Record a sale
        </p>
        <p className="mt-2 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          PLUS oil sales share the byproduct-sales form (carbon black, metal
          scrap, PLUS oil all funnel through the same buyer ledger).
        </p>
        <Link
          href="/app/warehouse/byproduct-sales?product=plus_oil"
          className="mt-4 inline-block border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
        >
          Use byproduct sales form →
        </Link>
      </section>
    </div>
  );
}

function KpiTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-rule bg-bg-soft p-4">
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
        {label}
      </p>
      <p className="mt-2 font-display text-2xl tracking-editorial text-ink">{value}</p>
    </div>
  );
}
