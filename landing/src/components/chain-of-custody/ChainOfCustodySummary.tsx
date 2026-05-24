/**
 * Chain-of-custody summary widget — drill-down.
 *
 * Six stage rows over one consignment (upstream → production → inland →
 * ocean → UTB → outbound). Each row is a collapsible <details>: clicking
 * the row reveals the underlying detail table inline (production links,
 * inland shipments, ocean BL legs, PoS list). Rows without a detail node
 * remain non-interactive.
 *
 * Audit framing: explicit consignment_code + counts + first/last document
 * numbers + kg totals. No full eRSV number lists in the summary line —
 * those live in the renderer PDFs and in the ledger (per
 * ``docs/mass-balance-allocation-policy.md`` §5).
 */
import {
  Recycle,
  Factory,
  Truck,
  Ship,
  Warehouse,
  PackageOpen,
  ChevronRight,
} from 'lucide-react';

export interface ChainSummaryData {
  consignment_id: number;
  consignment_code: string;
  status: string;
  product_grade: string;
  consignment_kg: string | null;
  prod_date_from: string | null;
  prod_date_to: string | null;

  // Upstream
  inbound_ersv_count: number;
  inbound_supplier_count: number;
  inbound_feedstock_kg: string | null;

  // Plant production (window)
  production_days: number;
  plant_production_kg: string | null;

  // Inland CO
  inland_container_count: number;
  inland_ersv_alloc_count: number;
  inland_ersv_first: string | null;
  inland_ersv_last: string | null;
  inland_kg_total: string | null;

  // Ocean BL
  bl_ocean_count: number;
  bl_ocean_refs: string | null;

  // UTB transload
  utb_stock_residual_kg: string | null;

  // Downstream PoS / outbound eRSV
  pos_count: number;
  pos_kg_total: string | null;
  pos_with_outbound_ersv: number;
  pos_first: string | null;
  pos_last: string | null;

  // Allocation link table — completeness flag
  production_link_days: number;
  production_link_kg: string | null;
}

export type ChainRowKey =
  | 'upstream'
  | 'production'
  | 'inland'
  | 'ocean'
  | 'utb'
  | 'outbound';

export type ChainDetails = Partial<Record<ChainRowKey, React.ReactNode>>;

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const numFmt3 = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 3,
});
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtKg(v: string | null | undefined, decimals = 0): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  const fmt = decimals > 0 ? numFmt3 : numFmt;
  return `${fmt.format(n)} kg`;
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtCount(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return numFmt.format(n);
}

function fmtRange(first: string | null, last: string | null): string {
  if (!first && !last) return '—';
  if (first === last || !last) return first ?? '—';
  return `${first} … ${last}`;
}

function fmtYield(prodKg: string | null, feedstockKg: string | null): string {
  const p = Number(prodKg);
  const f = Number(feedstockKg);
  if (!Number.isFinite(p) || !Number.isFinite(f) || f <= 0) return '—';
  return `${((p / f) * 100).toFixed(1)} %`;
}

interface Props {
  data: ChainSummaryData;
  /** Optional inline detail nodes (rendered when the user opens the row). */
  details?: ChainDetails;
}

export function ChainOfCustodySummary({ data, details = {} }: Props) {
  // Allocation completeness — link kg vs consignment kg
  const linkKg = Number(data.production_link_kg ?? 0);
  const cKg = Number(data.consignment_kg ?? 0);
  const linkOk =
    Number.isFinite(linkKg) &&
    Number.isFinite(cKg) &&
    cKg > 0 &&
    Math.abs(linkKg - cKg) < 1;

  // Outbound eRSV completeness — PoS allocated vs total
  const posComplete =
    data.pos_count > 0 && data.pos_with_outbound_ersv === data.pos_count;

  return (
    <div className="mb-10 border border-rule bg-bg-soft">
      {/* Header strip */}
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-rule bg-bg px-4 py-3">
        <div>
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
            Mass-balance recap · {data.consignment_code}
          </p>
          <p className="mt-0.5 font-mono text-[0.72rem] text-ink-soft">
            {fmtDate(data.prod_date_from)} → {fmtDate(data.prod_date_to)} ·{' '}
            {data.product_grade}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span
            className={`inline-block border px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.1em] ${
              linkOk
                ? 'border-olive-deep bg-olive-deep/10 text-olive-deep'
                : 'border-accent bg-accent/5 text-accent'
            }`}
            title="Allocation link: kg_allocated (consignment_production_link) vs consignment.total_kg"
          >
            link {linkOk ? 'balanced' : 'mismatch'}
          </span>
          <span
            className={`inline-block border px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.1em] ${
              posComplete
                ? 'border-olive-deep bg-olive-deep/10 text-olive-deep'
                : 'border-rule bg-bg text-ink-soft'
            }`}
            title="PoS rows with ersv_outbound_no allocated"
          >
            eRSV out {data.pos_with_outbound_ersv}/{data.pos_count}
          </span>
        </div>
      </div>

      {/* Body — six rows, each optionally collapsible with inline detail */}
      <div className="divide-y divide-rule">
        <Row
          icon={Recycle}
          label="Upstream (ELT feedstock)"
          primary={`${fmtCount(data.inbound_ersv_count)} eRSV · ${fmtCount(
            data.inbound_supplier_count,
          )} suppliers`}
          secondary={`${fmtKg(data.inbound_feedstock_kg)} input · window ${fmtDate(
            data.prod_date_from,
          )} → ${fmtDate(data.prod_date_to)}`}
          detail={details.upstream}
        />
        <Row
          icon={Factory}
          label="Production (Girardot CO)"
          primary={`${fmtCount(data.production_days)} days · ${fmtKg(
            data.plant_production_kg,
            3,
          )} plant total`}
          secondary={`Yield ${fmtYield(
            data.plant_production_kg,
            data.inbound_feedstock_kg,
          )} · allocated to consignment ${fmtKg(
            data.production_link_kg,
            3,
          )} (${fmtCount(data.production_link_days)} days)`}
          detail={details.production}
        />
        <Row
          icon={Truck}
          label="Inland (Girardot → Cartagena)"
          primary={`${fmtCount(data.inland_container_count)} containers · ${fmtCount(
            data.inland_ersv_alloc_count,
          )} inland eRSV`}
          secondary={`${fmtKg(data.inland_kg_total)} net · ${fmtRange(
            data.inland_ersv_first,
            data.inland_ersv_last,
          )}`}
          detail={details.inland}
        />
        <Row
          icon={Ship}
          label="Ocean BL (Cartagena → Rotterdam)"
          primary={`${fmtCount(data.bl_ocean_count)} BL`}
          secondary={data.bl_ocean_refs ?? '—'}
          detail={details.ocean}
        />
        <Row
          icon={Warehouse}
          label="UTB transload (Rotterdam)"
          primary={
            data.utb_stock_residual_kg
              ? `Stock residual ${fmtKg(data.utb_stock_residual_kg)}`
              : 'No transload leg'
          }
          secondary={null}
          detail={details.utb}
        />
        <Row
          icon={PackageOpen}
          label="Outbound (PoS → Crown Oil UK)"
          primary={`${fmtCount(data.pos_count)} PoS · ${fmtKg(
            data.pos_kg_total,
          )} delivered`}
          secondary={`${fmtRange(data.pos_first, data.pos_last)} · eRSV out ${
            data.pos_with_outbound_ersv
          }/${data.pos_count}`}
          detail={details.outbound}
        />
      </div>
    </div>
  );
}

interface RowProps {
  icon: React.ElementType;
  label: string;
  primary: string;
  secondary: string | null;
  detail?: React.ReactNode;
}

function Row({ icon: Icon, label, primary, secondary, detail }: RowProps) {
  const hasDetail = detail !== undefined && detail !== null && detail !== false;

  const body = (
    <>
      <div className="flex h-7 w-7 shrink-0 items-center justify-center border border-rule bg-bg">
        <Icon className="h-3.5 w-3.5 text-ink-soft" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-ink-mute">
          {label}
        </p>
        <p className="mt-0.5 font-mono text-[0.78rem] text-ink tabular-nums">
          {primary}
        </p>
        {secondary && (
          <p className="mt-0.5 font-mono text-[0.7rem] text-ink-soft tabular-nums">
            {secondary}
          </p>
        )}
      </div>
      {hasDetail && (
        <ChevronRight
          className="mt-1 h-3.5 w-3.5 shrink-0 text-ink-mute transition-transform group-open:rotate-90"
          aria-hidden
        />
      )}
    </>
  );

  if (!hasDetail) {
    return <div className="flex gap-3 px-4 py-2.5">{body}</div>;
  }

  return (
    <details className="group">
      <summary className="flex cursor-pointer list-none gap-3 px-4 py-2.5 hover:bg-bg [&::-webkit-details-marker]:hidden">
        {body}
      </summary>
      <div className="border-t border-rule/60 bg-bg px-4 py-4">{detail}</div>
    </details>
  );
}
