import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Row = components['schemas']['ClosureStatusRow'];
type Bucket = 'ok' | 'warn' | 'alert' | 'no_input' | 'no_output';

const BUCKETS: Bucket[] = ['ok', 'warn', 'alert', 'no_input', 'no_output'];

const BUCKET_LABEL: Record<Bucket, string> = {
  ok: 'OK',
  warn: 'Warn',
  alert: 'Alert',
  no_input: 'No input',
  no_output: 'No output',
};

const BUCKET_DESC: Record<Bucket, string> = {
  ok: '|diff| ≤ 2%',
  warn: '2% < |diff| ≤ 5%',
  alert: '|diff| > 5%',
  no_input: 'input = 0',
  no_output: 'output = 0',
};

const BUCKET_DOT: Record<Bucket, string> = {
  ok: 'bg-olive-deep',
  warn: 'bg-olive',
  alert: 'bg-accent',
  no_input: 'bg-ink-mute',
  no_output: 'bg-ink-soft',
};

const BUCKET_ROW: Record<Bucket, string> = {
  ok: 'border-l-2 border-l-olive-deep',
  warn: 'border-l-2 border-l-olive',
  alert: 'border-l-2 border-l-accent',
  no_input: 'border-l-2 border-l-ink-mute',
  no_output: 'border-l-2 border-l-ink-soft',
};

export const dynamic = 'force-dynamic';

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const pctFmt = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function sanitizeDate(v: string | undefined): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
}

function sanitizeBucket(v: string | undefined): Bucket | undefined {
  return v && (BUCKETS as string[]).includes(v) ? (v as Bucket) : undefined;
}

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return numFmt.format(n);
}

function fmtPct(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return pctFmt.format(n);
}

function buildHref(base: string, params: Record<string, string | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) sp.set(k, v);
  const q = sp.toString();
  return q ? `${base}?${q}` : base;
}

interface PageProps {
  searchParams: { from?: string; to?: string; bucket?: string };
}

export default async function ClosureStatusPage({ searchParams }: PageProps) {
  const from = sanitizeDate(searchParams.from);
  const to = sanitizeDate(searchParams.to);
  const bucketFilter = sanitizeBucket(searchParams.bucket);

  let rows: Row[] = [];
  let fetchError: string | null = null;

  try {
    rows = await apiGet<Row[]>('/reports/closure-status', {
      query: { date_from: from, date_to: to },
    });
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const counts: Record<Bucket, number> = {
    ok: 0,
    warn: 0,
    alert: 0,
    no_input: 0,
    no_output: 0,
  };
  for (const r of rows) {
    if ((BUCKETS as string[]).includes(r.bucket)) counts[r.bucket as Bucket]++;
  }
  const total = rows.length;
  const filtered = bucketFilter ? rows.filter((r) => r.bucket === bucketFilter) : rows;

  const csvHref = buildHref('/api/reports/closure-status/csv', {
    from,
    to,
    bucket: bucketFilter,
  });

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">Report</p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Daily closure
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Balance traffic light by day · {total} days in period
          {from || to ? ` · filter ${from ?? '…'} → ${to ?? '…'}` : ''}
          {bucketFilter ? ` · bucket = ${BUCKET_LABEL[bucketFilter]}` : ''}
        </p>
      </header>

      <section className="mt-6 flex flex-wrap items-end justify-end gap-4 border-b border-rule pb-6">
        <form
          method="GET"
          action="/app/reports/closure-status"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          {bucketFilter && <input type="hidden" name="bucket" value={bucketFilter} />}
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
            href="/app/reports/closure-status"
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

      <section className="mt-6 grid grid-cols-2 sm:grid-cols-5 gap-3">
        {BUCKETS.map((b) => {
          const active = bucketFilter === b;
          const href = buildHref('/app/reports/closure-status', {
            from,
            to,
            bucket: active ? undefined : b,
          });
          const pct = total > 0 ? (counts[b] / total) * 100 : 0;
          return (
            <Link
              key={b}
              href={href}
              className={`border bg-bg-soft p-4 hover:border-ink ${
                active ? 'border-ink' : 'border-rule'
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`inline-block h-2.5 w-2.5 rounded-full ${BUCKET_DOT[b]}`} />
                <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
                  {BUCKET_LABEL[b]}
                </p>
              </div>
              <p className="mt-2 font-display text-2xl tracking-editorial text-ink">{counts[b]}</p>
              <p className="mt-1 font-mono text-[0.65rem] text-ink-mute">
                {pctFmt.format(pct)}% · {BUCKET_DESC[b]}
              </p>
            </Link>
          );
        })}
      </section>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Day</Th>
              <Th>Status</Th>
              <ThNum>Input kg</ThNum>
              <ThNum>Output kg</ThNum>
              <ThNum>Closure %</ThNum>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && !fetchError && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-ink-mute">
                  No days match the selected filter.
                </td>
              </tr>
            )}
            {filtered.map((r) => {
              const b = (BUCKETS as string[]).includes(r.bucket) ? (r.bucket as Bucket) : 'ok';
              return (
                <tr
                  key={r.day}
                  className={`border-b border-rule/60 last:border-b-0 hover:bg-bg ${BUCKET_ROW[b]}`}
                >
                  <Td className="text-ink">{r.day}</Td>
                  <Td>
                    <span className="inline-flex items-center gap-1.5">
                      <span className={`inline-block h-2 w-2 rounded-full ${BUCKET_DOT[b]}`} />
                      <span className="text-ink-soft">{BUCKET_LABEL[b]}</span>
                    </span>
                  </Td>
                  <TdNum>{fmtKg(r.input_total_kg)}</TdNum>
                  <TdNum>{fmtKg(r.output_total_kg)}</TdNum>
                  <TdNum
                    className={
                      b === 'alert' ? 'text-accent' : b === 'warn' ? 'text-olive' : 'text-ink'
                    }
                  >
                    {fmtPct(r.closure_diff_pct)}
                  </TdNum>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
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
