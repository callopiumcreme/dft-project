import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { SupplierPie, type PieSlice } from '../../_components/supplier-pie';

type Row = components['schemas']['BySupplierRow'];

export const dynamic = 'force-dynamic';

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const REDIST_POOL = new Set(['EFFICIEN', 'KALTIRE', 'PYRCOM', 'BOLDER', 'ESENTTIA']);
const REDIST_TARGET: Record<string, number> = {
  EFFICIEN: 35,
  KALTIRE: 30,
  PYRCOM: 20,
  BOLDER: 10,
  ESENTTIA: 5,
};
const REDIST_FROM = '2025-02-01';
const REDIST_TO = '2025-08-31';
const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const pctFmt = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

function sanitizeDate(v: string | undefined): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
}

function buildHref(base: string, params: Record<string, string | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) sp.set(k, v);
  const q = sp.toString();
  return q ? `${base}?${q}` : base;
}

interface PageProps {
  searchParams: { from?: string; to?: string };
}

export default async function BySupplierPage({ searchParams }: PageProps) {
  const from = sanitizeDate(searchParams.from);
  const to = sanitizeDate(searchParams.to);

  let rows: Row[] = [];
  let fetchError: string | null = null;

  try {
    rows = await apiGet<Row[]>('/reports/by-supplier', {
      query: { date_from: from, date_to: to },
    });
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const sorted = [...rows].sort((a, b) => Number(b.total_input_kg) - Number(a.total_input_kg));
  const totalKg = sorted.reduce((s, r) => s + (Number(r.total_input_kg) || 0), 0);
  const totalEntries = sorted.reduce((s, r) => s + r.entries, 0);
  const certKg = sorted
    .filter((r) => REDIST_POOL.has(r.supplier_code))
    .reduce((s, r) => s + (Number(r.total_input_kg) || 0), 0);
  const inRedistWindow = from === REDIST_FROM && to === REDIST_TO;

  const slices: PieSlice[] = sorted.map((r) => {
    const v = Number(r.total_input_kg) || 0;
    return {
      name: r.supplier_code,
      value: v,
      pct: totalKg > 0 ? (v / totalKg) * 100 : 0,
    };
  });

  const csvHref = buildHref('/api/reports/by-supplier/csv', { from, to });

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">Report</p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">By supplier</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Input distribution by supplier · {sorted.length} suppliers
          {from || to ? ` · filter ${from ?? '…'} → ${to ?? '…'}` : ''}
        </p>
      </header>

      <section className="mt-6 flex flex-wrap items-end justify-end gap-4 border-b border-rule pb-6">
        <form
          method="GET"
          action="/app/reports/by-supplier"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">From</span>
            <input
              type="date"
              name="from"
              defaultValue={from ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">To</span>
            <input
              type="date"
              name="to"
              defaultValue={to ?? ''}
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
            href="/app/reports/by-supplier"
            className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
          >
            Reset
          </Link>
          <a
            href={csvHref}
            className="border border-olive-deep bg-olive-deep px-3 py-1.5 text-bg hover:bg-olive"
            download
          >
            Export CSV
          </a>
        </form>
      </section>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      <div
        className={`mt-6 border p-4 font-mono text-[0.72rem] leading-relaxed ${
          inRedistWindow
            ? 'border-olive-deep/40 bg-olive-deep/5 text-ink-soft'
            : 'border-rule bg-bg-soft text-ink-soft'
        }`}
      >
        {inRedistWindow ? (
          <>
            <span className="text-ink">RTFO 0016 window active</span> — filter
            matches Feb-Aug 2025; % Pool should equal Target within ±0.04 pp.
          </>
        ) : (
          <>
            <span className="text-ink">% Pool ≠ Target?</span> Migration 0016
            redistribution targets apply to Feb-Aug 2025 only — current filter
            is{' '}
            <span className="text-ink">
              {from ?? '…'} → {to ?? '…'}
            </span>
            .{' '}
            <Link
              href={buildHref('/app/reports/by-supplier', {
                from: REDIST_FROM,
                to: REDIST_TO,
              })}
              className="underline decoration-dotted underline-offset-2 hover:text-ink"
            >
              Apply Feb 1 → Aug 31 filter
            </Link>{' '}
            to verify the 35 / 30 / 20 / 10 / 5 match.
          </>
        )}
      </div>

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiTile label="Suppliers" value={String(sorted.length)} />
        <KpiTile label="Total input" value={`${numFmt.format(totalKg)} kg`} />
        <KpiTile label="Total entries" value={numFmt.format(totalEntries)} />
      </section>

      <section className="mt-6 grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2 border border-rule bg-bg-soft p-5">
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
            Input share by supplier
          </p>
          <div className="mt-3">
            <SupplierPie data={slices} />
          </div>
        </div>

        <div className="lg:col-span-3 border border-rule bg-bg-soft overflow-x-auto">
          <table className="w-full border-collapse font-mono text-[0.72rem]">
            <thead className="border-b border-rule bg-bg">
              <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                <Th>#</Th>
                <Th>Code</Th>
                <Th>Name</Th>
                <ThNum>Input kg</ThNum>
                <ThNum>% Total</ThNum>
                <ThNum>% Pool</ThNum>
                <ThNum>Target</ThNum>
                <ThNum>Entries</ThNum>
                <ThNum>Days</ThNum>
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 && !fetchError && (
                <tr>
                  <td colSpan={9} className="px-3 py-6 text-center text-ink-mute">
                    No suppliers in selected period.
                  </td>
                </tr>
              )}
              {sorted.map((r, i) => {
                const v = Number(r.total_input_kg) || 0;
                const pct = totalKg > 0 ? (v / totalKg) * 100 : 0;
                const inPool = REDIST_POOL.has(r.supplier_code);
                const pctCert = inPool && certKg > 0 ? (v / certKg) * 100 : null;
                const target = REDIST_TARGET[r.supplier_code];
                return (
                  <tr
                    key={r.supplier_id}
                    className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                  >
                    <Td className="text-ink-mute">{i + 1}</Td>
                    <Td className="text-ink">{r.supplier_code}</Td>
                    <Td className="text-ink-soft">{r.supplier_name}</Td>
                    <TdNum>{numFmt.format(v)}</TdNum>
                    <TdNum>{pctFmt.format(pct)}</TdNum>
                    <TdNum className={inPool ? '' : 'text-ink-mute'}>
                      {pctCert === null ? '—' : pctFmt.format(pctCert)}
                    </TdNum>
                    <TdNum className="text-ink-mute">
                      {target === undefined ? '—' : pctFmt.format(target)}
                    </TdNum>
                    <TdNum>{numFmt.format(r.entries)}</TdNum>
                    <TdNum>{numFmt.format(r.days)}</TdNum>
                  </tr>
                );
              })}
              {sorted.length > 0 && (
                <tr className="border-t border-rule bg-bg font-semibold text-ink">
                  <Td>—</Td>
                  <Td>TOT</Td>
                  <Td className="text-ink-soft">All suppliers</Td>
                  <TdNum>{numFmt.format(totalKg)}</TdNum>
                  <TdNum>100.0</TdNum>
                  <TdNum>
                    {certKg > 0 ? pctFmt.format((certKg / totalKg) * 100) : '—'}
                  </TdNum>
                  <TdNum className="text-ink-mute">100.0</TdNum>
                  <TdNum>{numFmt.format(totalEntries)}</TdNum>
                  <TdNum>—</TdNum>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <p className="mt-4 max-w-reading font-mono text-[0.7rem] leading-relaxed text-ink-mute">
        <span className="text-ink-soft">% Total</span> = share of input over all suppliers (includes
        LE5TON ≤5 TON aggregate + Jan-only suppliers BIOWASTE / LITOPLAS).{' '}
        <span className="text-ink-soft">% Pool</span> = share over the 5-supplier RTFO 0016
        redistribution pool only (EFFICIEN, KALTIRE, PYRCOM, BOLDER, ESENTTIA). Migration 0016
        rebalanced these five over Feb-Aug 2025 to <span className="text-ink-soft">Target</span>{' '}
        (35 / 30 / 20 / 10 / 5). Apply the Feb 1 → Aug 31 filter for an exact match within
        ±0.04 pp.
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

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 font-normal">{children}</th>;
}
function ThNum({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-right font-normal">{children}</th>;
}
function Td({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
function TdNum({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <td className={`px-3 py-2 text-right tabular-nums ${className}`}>{children}</td>;
}
