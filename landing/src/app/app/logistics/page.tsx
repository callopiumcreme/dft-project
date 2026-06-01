import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import { UmamiViewEvent } from '@/components/analytics/umami-view-event';
import type { ConsignmentSummary, ConsignmentStatus, OffTaker } from '@/types/logistics';

export const dynamic = 'force-dynamic';

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${numFmt.format(n)} kg`;
}

const STATUSES: ConsignmentStatus[] = [
  'draft',
  'loaded',
  'in_transit',
  'at_utb',
  'delivered_uk',
  'closed',
];

const STATUS_LABEL: Record<ConsignmentStatus, string> = {
  draft: 'Draft',
  loaded: 'Loaded',
  in_transit: 'In transit',
  at_utb: 'At UTB',
  delivered_uk: 'Delivered UK',
  closed: 'Closed',
};

const STATUS_PILL: Record<ConsignmentStatus, string> = {
  draft: 'border-rule bg-bg text-ink-mute',
  loaded: 'border-rule bg-bg text-ink-soft',
  in_transit: 'border-ink-soft bg-bg text-ink-soft',
  at_utb: 'border-ink bg-ink/5 text-ink',
  delivered_uk: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
  closed: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
};

function sanitizeStatus(v: string | undefined): ConsignmentStatus | undefined {
  return v && (STATUSES as string[]).includes(v) ? (v as ConsignmentStatus) : undefined;
}

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
function sanitizeDate(v: string | undefined): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
}

interface PageProps {
  searchParams: {
    status?: string;
    off_taker_id?: string;
    prod_date_from?: string;
    prod_date_to?: string;
  };
}

export default async function LogisticsPage({ searchParams }: PageProps) {
  const status = sanitizeStatus(searchParams.status);
  const offTakerId = searchParams.off_taker_id
    ? Number(searchParams.off_taker_id)
    : undefined;
  const prodFrom = sanitizeDate(searchParams.prod_date_from);
  const prodTo = sanitizeDate(searchParams.prod_date_to);

  let consignments: ConsignmentSummary[] = [];
  let offTakers: OffTaker[] = [];
  let fetchError: string | null = null;

  try {
    const [consRes, offRes] = await Promise.all([
      apiGet<ConsignmentSummary[]>('/consignments', {
        query: {
          ...(status ? { status } : {}),
          ...(offTakerId ? { off_taker_id: offTakerId } : {}),
          ...(prodFrom ? { prod_date_from: prodFrom } : {}),
          ...(prodTo ? { prod_date_to: prodTo } : {}),
        },
      }),
      apiGet<OffTaker[]>('/off-takers'),
    ]);
    consignments = consRes;
    offTakers = offRes;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  // KPI computations — sourced from chain-derived backend fields,
  // not from status alone (a consignment can be at_utb while having
  // already moved most kg downstream via delivery_uk legs).
  const totalConsignments = consignments.length;
  const totalKgShipped = consignments.reduce((s, c) => s + (Number(c.total_kg) || 0), 0);
  // UTB residual = real stock still sitting at UTB transload (kg_stock_residual)
  const utbResidual = consignments.reduce(
    (s, c) => s + (Number(c.kg_residual_utb) || 0),
    0,
  );
  // Delivered UK = sum of kg_out on delivery_uk legs (works regardless of status)
  const deliveredKg = consignments.reduce(
    (s, c) => s + (Number(c.kg_delivered_uk) || 0),
    0,
  );

  return (
    <div className="mx-auto max-w-editorial">
      <UmamiViewEvent
        name="view_logistics_list"
        data={{
          ...(status ? { status } : {}),
          ...(offTakerId ? { off_taker_id: offTakerId } : {}),
          ...(prodFrom ? { prod_date_from: prodFrom } : {}),
          ...(prodTo ? { prod_date_to: prodTo } : {}),
        }}
      />
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Downstream
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Logistics</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Chain of custody — DEV-P100 outbound · Girardot → Crown Oil UK
          {totalConsignments > 0 ? ` · ${totalConsignments} consignment${totalConsignments !== 1 ? 's' : ''}` : ''}
        </p>
      </header>

      {/* KPI tiles */}
      <section className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KpiTile label="Consignments" value={String(totalConsignments)} />
        <KpiTile label="Total shipped" value={fmtKg(String(totalKgShipped))} />
        <KpiTile label="UTB stock" value={fmtKg(String(utbResidual))} />
        <KpiTile label="Delivered UK" value={fmtKg(String(deliveredKg))} />
      </section>

      {/* Filters */}
      <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <form
          method="GET"
          action="/app/logistics"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Status</span>
            <select
              name="status"
              defaultValue={status ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            >
              <option value="">— all —</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Off-taker</span>
            <select
              name="off_taker_id"
              defaultValue={offTakerId ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            >
              <option value="">— all —</option>
              {offTakers.map((ot) => (
                <option key={ot.id} value={ot.id}>
                  {ot.code}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Prod from</span>
            <input
              type="date"
              name="prod_date_from"
              defaultValue={prodFrom ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Prod to</span>
            <input
              type="date"
              name="prod_date_to"
              defaultValue={prodTo ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <button
            type="submit"
            className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
          >
            Filter
          </button>
          <Link
            href="/app/logistics"
            className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
          >
            Reset
          </Link>
        </form>
      </section>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      {/* Table */}
      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Code</Th>
              <Th>Off-taker</Th>
              <Th>Product</Th>
              <ThNum>Total kg</ThNum>
              <Th>Status</Th>
              <Th className="text-right">
                <span className="sr-only">Open</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {consignments.length === 0 && !fetchError && (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-ink-mute">
                  No consignments match the selected filter.
                </td>
              </tr>
            )}
            {consignments.map((c) => {
              const s = (STATUSES as string[]).includes(c.status)
                ? (c.status as ConsignmentStatus)
                : 'draft';
              return (
                <tr
                  key={c.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink font-medium">{c.code}</Td>
                  <Td className="text-ink-soft">{c.off_taker?.code ?? '—'}</Td>
                  <Td className="text-ink-soft">{c.product_grade}</Td>
                  <TdNum>{fmtKg(c.total_kg)}</TdNum>
                  <Td>
                    <span
                      className={`inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${STATUS_PILL[s]}`}
                    >
                      {STATUS_LABEL[s]}
                    </span>
                  </Td>
                  <Td className="text-right">
                    <Link
                      href={`/app/logistics/${c.id}`}
                      className="text-ink-soft hover:text-ink"
                      aria-label={`Open consignment ${c.code}`}
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

      <p className="mt-4 max-w-reading font-mono text-[0.7rem] leading-relaxed text-ink-mute">
        Consignments aggregate ELT-derived DEV-P100 production from Girardot (Colombia) shipped to
        Crown Oil Ltd (UK) via Cartagena → Rotterdam → UTB BV Dordrecht transload → Bury.
        Mass-balance is tracked per shipment leg. UK regulator: RTFO/DfT — Crown Oil submits ROS.
      </p>
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

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-normal ${className}`}>{children}</th>;
}
function ThNum({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-right font-normal">{children}</th>;
}
function Td({
  className = '',
  children,
  title,
}: {
  className?: string;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <td className={`px-3 py-2 ${className}`} title={title}>
      {children}
    </td>
  );
}
function TdNum({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <td className={`px-3 py-2 text-right tabular-nums ${className}`}>{children}</td>;
}
