import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type DailyRow = components['schemas']['MassBalanceDailyRow'];
type MonthlyRow = components['schemas']['MassBalanceMonthlyRow'];

export const dynamic = 'force-dynamic';

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const numFmt = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 0 });
const pctFmt = new Intl.NumberFormat('it-IT', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function sanitizeDate(v: string | undefined): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
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
  searchParams: { view?: string; from?: string; to?: string };
}

export default async function MassBalancePage({ searchParams }: PageProps) {
  const view = searchParams.view === 'monthly' ? 'monthly' : 'daily';
  const from = sanitizeDate(searchParams.from);
  const to = sanitizeDate(searchParams.to);

  let rows: (DailyRow | MonthlyRow)[] = [];
  let fetchError: string | null = null;

  try {
    if (view === 'monthly') {
      rows = await apiGet<MonthlyRow[]>('/reports/mass-balance/monthly', {
        query: { date_from: from, date_to: to },
      });
    } else {
      rows = await apiGet<DailyRow[]>('/reports/mass-balance/daily', {
        query: { date_from: from, date_to: to, limit: 3660 },
      });
    }
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'errore sconosciuto';
  }

  const dateKey: 'day' | 'month' = view === 'monthly' ? 'month' : 'day';
  const csvHref = buildHref('/api/reports/mass-balance/csv', { view, from, to });
  const dailyHref = buildHref('/app/reports/mass-balance', { view: 'daily', from, to });
  const monthlyHref = buildHref('/app/reports/mass-balance', { view: 'monthly', from, to });

  const totalInput = rows.reduce((s, r) => s + (Number(r.input_total_kg) || 0), 0);
  const totalOutput = rows.reduce((s, r) => s + (Number(r.output_total_kg) || 0), 0);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">Report</p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Mass balance</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Bilancio input/output {view === 'monthly' ? 'per mese' : 'per giorno'} · {rows.length} righe
          {from || to ? ` · filtro ${from ?? '…'} → ${to ?? '…'}` : ''}
        </p>
      </header>

      <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <nav className="flex gap-1 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
          <Link
            href={dailyHref}
            className={
              view === 'daily'
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            Giornaliero
          </Link>
          <Link
            href={monthlyHref}
            className={
              view === 'monthly'
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            Mensile
          </Link>
        </nav>

        <form
          method="GET"
          action="/app/reports/mass-balance"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <input type="hidden" name="view" value={view} />
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Da</span>
            <input
              type="date"
              name="from"
              defaultValue={from ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">A</span>
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
            Filtra
          </button>
          <Link
            href={`/app/reports/mass-balance?view=${view}`}
            className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
          >
            Reset
          </Link>
          <a
            href={csvHref}
            className="border border-olive-deep bg-olive-deep px-3 py-1.5 text-bg hover:bg-olive"
            download
          >
            Esporta CSV
          </a>
        </form>
      </section>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Errore caricamento: {fetchError}
        </div>
      )}

      <section className="mt-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <KpiTile
            label="Periodo"
            value={`${rows.length} ${view === 'monthly' ? 'mesi' : 'giorni'}`}
          />
          <KpiTile label="Input totale" value={`${numFmt.format(totalInput)} kg`} />
          <KpiTile label="Output totale" value={`${numFmt.format(totalOutput)} kg`} />
        </div>
      </section>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full min-w-[1100px] border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>{view === 'monthly' ? 'Mese' : 'Giorno'}</Th>
              <ThNum>Input</ThNum>
              {view === 'daily' && <ThNum>Kg → produzione</ThNum>}
              <ThNum>EU</ThNum>
              <ThNum>Plus</ThNum>
              <ThNum>Carbon black</ThNum>
              <ThNum>Metal scrap</ThNum>
              <ThNum>H2O</ThNum>
              <ThNum>Syngas</ThNum>
              <ThNum>Losses</ThNum>
              <ThNum>Output EU</ThNum>
              <ThNum>Output totale</ThNum>
              <ThNum>Closure %</ThNum>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !fetchError && (
              <tr>
                <td
                  colSpan={view === 'monthly' ? 12 : 13}
                  className="px-3 py-6 text-center text-ink-mute"
                >
                  Nessun dato per il filtro selezionato.
                </td>
              </tr>
            )}
            {rows.map((r) => {
              const dateVal = (r as Record<string, string>)[dateKey];
              const closure = Number(r.closure_diff_pct);
              const closureClass =
                Number.isFinite(closure) && Math.abs(closure) >= 5 ? 'text-accent' : 'text-ink';
              return (
                <tr key={dateVal} className="border-b border-rule/60 last:border-b-0 hover:bg-bg">
                  <Td className="text-ink">{dateVal}</Td>
                  <TdNum>{fmtKg(r.input_total_kg)}</TdNum>
                  {view === 'daily' && (
                    <TdNum>{fmtKg((r as DailyRow).kg_to_production)}</TdNum>
                  )}
                  <TdNum>{fmtKg(r.eu_prod_kg)}</TdNum>
                  <TdNum>{fmtKg(r.plus_prod_kg)}</TdNum>
                  <TdNum>{fmtKg(r.carbon_black_kg)}</TdNum>
                  <TdNum>{fmtKg(r.metal_scrap_kg)}</TdNum>
                  <TdNum>{fmtKg(r.h2o_kg)}</TdNum>
                  <TdNum>{fmtKg(r.gas_syngas_kg)}</TdNum>
                  <TdNum>{fmtKg(r.losses_kg)}</TdNum>
                  <TdNum>{fmtKg(r.output_eu_kg)}</TdNum>
                  <TdNum>{fmtKg(r.output_total_kg)}</TdNum>
                  <TdNum className={closureClass}>{fmtPct(r.closure_diff_pct)}</TdNum>
                </tr>
              );
            })}
          </tbody>
        </table>
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
