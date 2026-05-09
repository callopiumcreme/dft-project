import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { SupplierPie, type PieSlice } from '../../_components/supplier-pie';

type Row = components['schemas']['BySupplierRow'];

export const dynamic = 'force-dynamic';

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
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
                <ThNum>%</ThNum>
                <ThNum>Entries</ThNum>
                <ThNum>Days</ThNum>
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 && !fetchError && (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-ink-mute">
                    No suppliers in selected period.
                  </td>
                </tr>
              )}
              {sorted.map((r, i) => {
                const v = Number(r.total_input_kg) || 0;
                const pct = totalKg > 0 ? (v / totalKg) * 100 : 0;
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
                    <TdNum>{numFmt.format(r.entries)}</TdNum>
                    <TdNum>{numFmt.format(r.days)}</TdNum>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
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
