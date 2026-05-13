import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { MonthQuickPicker } from './month-quick-picker';
import { buildMonthOptions } from './month-utils';

type DailyRow = components['schemas']['MassBalanceDailyRow'];
type MonthlyRow = components['schemas']['MassBalanceMonthlyRow'];
type DailyInput = components['schemas']['DailyInputRead'];
type Supplier = components['schemas']['SupplierRead'];
type Certificate = components['schemas']['CertificateRead'];
type Contract = components['schemas']['ContractRead'];

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

function sanitizeSupplierId(v: string | undefined): string | undefined {
  if (!v) return undefined;
  const n = Number(v);
  return Number.isInteger(n) && n > 0 ? String(n) : undefined;
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

function fmtTime(v: string | null | undefined): string {
  if (!v) return '—';
  return v.length >= 5 ? v.slice(0, 5) : v;
}

function describeLoaded(
  car: string | null | undefined,
  truck: string | null | undefined,
  special: string | null | undefined,
): { types: { label: string; value: string }[] } {
  const parts: { label: string; value: string }[] = [];
  for (const [label, raw] of [
    ['CAR', car],
    ['TRUCK', truck],
    ['SPECIAL', special],
  ] as const) {
    const n = Number(raw);
    if (Number.isFinite(n) && n > 0) parts.push({ label, value: String(raw) });
  }
  return { types: parts };
}

function buildHref(base: string, params: Record<string, string | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) sp.set(k, v);
  const q = sp.toString();
  return q ? `${base}?${q}` : base;
}

interface PageProps {
  searchParams: { view?: string; from?: string; to?: string; supplier_id?: string };
}

const DAILY_GRID_TEMPLATE =
  'minmax(180px,1.4fr) minmax(110px,1fr) minmax(110px,1fr) minmax(90px,0.8fr)';

export default async function MassBalancePage({ searchParams }: PageProps) {
  const view = searchParams.view === 'monthly' ? 'monthly' : 'daily';
  const from = sanitizeDate(searchParams.from);
  const to = sanitizeDate(searchParams.to);
  const supplierId = sanitizeSupplierId(searchParams.supplier_id);

  let dailyRows: DailyRow[] = [];
  let monthlyRows: MonthlyRow[] = [];
  let allMonths: MonthlyRow[] = [];
  let entriesByDay: Map<string, DailyInput[]> = new Map();
  let supplierMap: Map<number, Supplier> = new Map();
  let certificateMap: Map<number, Certificate> = new Map();
  let contractMap: Map<number, Contract> = new Map();
  let fetchError: string | null = null;

  try {
    const allMonthsPromise = apiGet<MonthlyRow[]>('/reports/mass-balance/monthly', {});
    const suppliersPromise = apiGet<Supplier[]>('/suppliers', {
      query: { active_only: 'false' },
    });
    if (view === 'monthly') {
      const [filtered, all, suppliers] = await Promise.all([
        apiGet<MonthlyRow[]>('/reports/mass-balance/monthly', {
          query: { date_from: from, date_to: to, supplier_id: supplierId },
        }),
        allMonthsPromise,
        suppliersPromise,
      ]);
      monthlyRows = filtered;
      allMonths = all;
      supplierMap = new Map(suppliers.map((s) => [s.id, s]));
    } else {
      const [daily, entries, suppliers, certs, contracts, all] = await Promise.all([
        apiGet<DailyRow[]>('/reports/mass-balance/daily', {
          query: { date_from: from, date_to: to, supplier_id: supplierId, limit: 3660 },
        }),
        apiGet<DailyInput[]>('/daily-inputs', {
          query: { date_from: from, date_to: to, supplier_id: supplierId, limit: 1000 },
        }),
        suppliersPromise,
        apiGet<Certificate[]>('/certificates'),
        apiGet<Contract[]>('/contracts'),
        allMonthsPromise,
      ]);
      dailyRows = daily;
      allMonths = all;
      supplierMap = new Map(suppliers.map((s) => [s.id, s]));
      certificateMap = new Map(certs.map((c) => [c.id, c]));
      contractMap = new Map(contracts.map((c) => [c.id, c]));
      entriesByDay = new Map();
      for (const e of entries) {
        const list = entriesByDay.get(e.entry_date) ?? [];
        list.push(e);
        entriesByDay.set(e.entry_date, list);
      }
      for (const list of entriesByDay.values()) {
        list.sort((a, b) => (a.entry_time ?? '').localeCompare(b.entry_time ?? ''));
      }
    }
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const monthOptions = buildMonthOptions(allMonths.map((m) => m.month));

  const rowCount = view === 'monthly' ? monthlyRows.length : dailyRows.length;
  const csvHref = buildHref('/api/reports/mass-balance/csv', {
    view,
    from,
    to,
    supplier_id: supplierId,
  });
  const dailyHref = buildHref('/app/reports/mass-balance', {
    view: 'daily',
    from,
    to,
    supplier_id: supplierId,
  });
  const monthlyHref = buildHref('/app/reports/mass-balance', {
    view: 'monthly',
    from,
    to,
    supplier_id: supplierId,
  });
  const supplierLabel =
    supplierId != null
      ? (() => {
          const s = supplierMap.get(Number(supplierId));
          return s?.name ?? s?.code ?? `#${supplierId}`;
        })()
      : null;

  const sumRows: {
    input_total_kg?: string | null;
    output_total_kg?: string | null;
    eu_prod_litres?: string | null;
    plus_prod_litres?: string | null;
    total_prod_litres?: string | null;
  }[] = view === 'monthly' ? monthlyRows : dailyRows;
  const totalInput = sumRows.reduce((s, r) => s + (Number(r.input_total_kg) || 0), 0);
  const totalOutput = sumRows.reduce((s, r) => s + (Number(r.output_total_kg) || 0), 0);
  const totalEuLitres = sumRows.reduce((s, r) => s + (Number(r.eu_prod_litres) || 0), 0);
  const totalPlusLitres = sumRows.reduce((s, r) => s + (Number(r.plus_prod_litres) || 0), 0);
  const totalLitres = sumRows.reduce((s, r) => s + (Number(r.total_prod_litres) || 0), 0);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">Report</p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Mass balance</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Input/output balance {view === 'monthly' ? 'by month' : 'by day'} · {rowCount} rows
          {from || to ? ` · filter ${from ?? '…'} → ${to ?? '…'}` : ''}
          {supplierLabel ? ` · supplier ${supplierLabel}` : ''}
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
            Daily
          </Link>
          <Link
            href={monthlyHref}
            className={
              view === 'monthly'
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            Monthly
          </Link>
        </nav>

        <form
          method="GET"
          action="/app/reports/mass-balance"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <input type="hidden" name="view" value={view} />
          <MonthQuickPicker options={monthOptions} view={view} from={from} to={to} />
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
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Supplier</span>
            <select
              name="supplier_id"
              defaultValue={supplierId ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            >
              <option value="">All suppliers</option>
              {Array.from(supplierMap.values())
                .sort((a, b) =>
                  (a.name ?? a.code ?? '').localeCompare(b.name ?? b.code ?? ''),
                )
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name ?? s.code ?? `#${s.id}`}
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
            Export CSV
          </a>
        </form>
      </section>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      <section className="mt-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <KpiTile
            label="Period"
            value={`${rowCount} ${view === 'monthly' ? 'months' : 'days'}`}
          />
          <KpiTile label="Total input" value={`${numFmt.format(totalInput)} kg`} />
          <KpiTile label="Total output" value={`${numFmt.format(totalOutput)} kg`} />
          <KpiTile label="Total EU (L)" value={`${numFmt.format(totalEuLitres)} L`} />
          <KpiTile label="Total Plus (L)" value={`${numFmt.format(totalPlusLitres)} L`} />
          <KpiTile label="Total prod (L)" value={`${numFmt.format(totalLitres)} L`} />
        </div>
      </section>

      {view === 'monthly' ? (
        <MonthlyTable rows={monthlyRows} hasError={!!fetchError} />
      ) : (
        <DailyAccordion
          rows={dailyRows}
          entriesByDay={entriesByDay}
          supplierMap={supplierMap}
          certificateMap={certificateMap}
          contractMap={contractMap}
          hasError={!!fetchError}
        />
      )}
    </div>
  );
}

const MONTHLY_GRID_TEMPLATE =
  'minmax(140px,1fr) minmax(110px,1fr) minmax(110px,1fr) minmax(90px,0.8fr)';

function MonthlyTable({ rows, hasError }: { rows: MonthlyRow[]; hasError: boolean }) {
  return (
    <section className="mt-6 border border-rule bg-bg-soft">
      <div>
        <div
          style={{ gridTemplateColumns: MONTHLY_GRID_TEMPLATE }}
          className="grid gap-x-3 border-b border-rule bg-bg px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.12em] text-ink-mute"
        >
          <span>Month</span>
          <span className="text-right">Input</span>
          <span className="text-right">Output total</span>
          <span className="text-right">Closure %</span>
        </div>

        {rows.length === 0 && !hasError && (
          <div className="px-3 py-6 text-center font-mono text-[0.72rem] text-ink-mute">
            No data for selected filter.
          </div>
        )}

        {rows.map((r, idx) => {
          const closure = Number(r.closure_diff_pct);
          const closureClass =
            Number.isFinite(closure) && Math.abs(closure) >= 5 ? 'text-accent' : 'text-ink';
          return (
            <details
              key={r.month}
              open={idx === 0}
              className="group border-b border-rule/60 last:border-b-0 open:bg-bg/40 open:border-l-4 open:border-l-olive-deep"
            >
              <summary
                style={{ gridTemplateColumns: MONTHLY_GRID_TEMPLATE }}
                className="grid cursor-pointer list-none gap-x-3 px-3 py-2 font-mono text-[0.72rem] text-ink hover:bg-bg group-open:bg-olive-deep group-open:text-bg group-open:font-medium [&::-webkit-details-marker]:hidden"
              >
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className="inline-block w-2 text-ink-mute transition-transform group-open:rotate-90 group-open:text-bg"
                  >
                    ›
                  </span>
                  <span>{r.month}</span>
                </span>
                <span className="text-right tabular-nums">{fmtKg(r.input_total_kg)}</span>
                <span className="text-right tabular-nums">{fmtKg(r.output_total_kg)}</span>
                <span className={`text-right tabular-nums ${closureClass} group-open:text-bg`}>
                  {fmtPct(r.closure_diff_pct)}
                </span>
              </summary>

              <div className="border-t-2 border-olive-deep bg-olive-deep/5 px-3 py-3">
                <p className="mb-2 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
                  Production breakdown
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[0.7rem]">
                  <BreakdownTile label="EU prod" value={r.eu_prod_kg} />
                  <BreakdownTile label="Plus prod" value={r.plus_prod_kg} />
                  <BreakdownTile label="Output EU" value={r.output_eu_kg} />
                  <BreakdownTile label="Carbon black" value={r.carbon_black_kg} />
                  <BreakdownTile label="Metal scrap" value={r.metal_scrap_kg} />
                  <BreakdownTile label="H2O" value={r.h2o_kg} />
                  <BreakdownTile label="Syngas" value={r.gas_syngas_kg} />
                  <BreakdownTile label="Losses" value={r.losses_kg} />
                </div>
                <p className="mt-3 mb-2 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
                  Volume (litres)
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[0.7rem]">
                  <BreakdownTile label="EU prod" value={r.eu_prod_litres} unit="L" />
                  <BreakdownTile label="Plus prod" value={r.plus_prod_litres} unit="L" />
                  <BreakdownTile label="Total prod" value={r.total_prod_litres} unit="L" />
                </div>
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}

function DailyAccordion({
  rows,
  entriesByDay,
  supplierMap,
  certificateMap,
  contractMap,
  hasError,
}: {
  rows: DailyRow[];
  entriesByDay: Map<string, DailyInput[]>;
  supplierMap: Map<number, Supplier>;
  certificateMap: Map<number, Certificate>;
  contractMap: Map<number, Contract>;
  hasError: boolean;
}) {
  return (
    <section className="mt-6 border border-rule bg-bg-soft">
      <div>
        <div
          style={{ gridTemplateColumns: DAILY_GRID_TEMPLATE }}
          className="grid gap-x-3 border-b border-rule bg-bg px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.12em] text-ink-mute"
        >
          <span>Day</span>
          <span className="text-right">Input</span>
          <span className="text-right">Output total</span>
          <span className="text-right">Closure %</span>
        </div>

        {rows.length === 0 && !hasError && (
          <div className="px-3 py-6 text-center font-mono text-[0.72rem] text-ink-mute">
            No data for selected filter.
          </div>
        )}

        {rows.map((r, idx) => {
          const closure = Number(r.closure_diff_pct);
          const closureClass =
            Number.isFinite(closure) && Math.abs(closure) >= 5 ? 'text-accent' : 'text-ink';
          const dayEntries = entriesByDay.get(r.day) ?? [];
          return (
            <details
              key={r.day}
              open={idx === 0}
              className="group border-b border-rule/60 last:border-b-0 open:bg-bg/40 open:border-l-4 open:border-l-olive-deep"
            >
              <summary
                style={{ gridTemplateColumns: DAILY_GRID_TEMPLATE }}
                className="grid cursor-pointer list-none gap-x-3 px-3 py-2 font-mono text-[0.72rem] text-ink hover:bg-bg group-open:bg-olive-deep group-open:text-bg group-open:font-medium [&::-webkit-details-marker]:hidden"
              >
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className="inline-block w-2 text-ink-mute transition-transform group-open:rotate-90 group-open:text-bg"
                  >
                    ›
                  </span>
                  <span>{r.day}</span>
                  <span className="text-ink-mute group-open:text-bg/70">· {dayEntries.length}</span>
                </span>
                <span className="text-right tabular-nums">{fmtKg(r.input_total_kg)}</span>
                <span className="text-right tabular-nums">{fmtKg(r.output_total_kg)}</span>
                <span className={`text-right tabular-nums ${closureClass} group-open:text-bg`}>
                  {fmtPct(r.closure_diff_pct)}
                </span>
              </summary>

              <div className="border-t-2 border-olive-deep bg-olive-deep/5 px-3 py-3 space-y-4">
                <div>
                  <p className="mb-2 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
                    Production breakdown
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[0.7rem]">
                    <BreakdownTile label="Kg → production" value={r.kg_to_production} />
                    <BreakdownTile label="EU prod" value={r.eu_prod_kg} />
                    <BreakdownTile label="Plus prod" value={r.plus_prod_kg} />
                    <BreakdownTile label="Output EU" value={r.output_eu_kg} />
                    <BreakdownTile label="Carbon black" value={r.carbon_black_kg} />
                    <BreakdownTile label="Metal scrap" value={r.metal_scrap_kg} />
                    <BreakdownTile label="H2O" value={r.h2o_kg} />
                    <BreakdownTile label="Syngas" value={r.gas_syngas_kg} />
                    <BreakdownTile label="Losses" value={r.losses_kg} />
                  </div>
                  <p className="mt-3 mb-2 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
                    Volume (litres)
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[0.7rem]">
                    <BreakdownTile label="EU prod" value={r.eu_prod_litres} unit="L" />
                    <BreakdownTile label="Plus prod" value={r.plus_prod_litres} unit="L" />
                    <BreakdownTile label="Total prod" value={r.total_prod_litres} unit="L" />
                  </div>
                </div>
                {dayEntries.length === 0 ? (
                  <p className="font-mono text-[0.7rem] text-ink-mute">
                    No truck entries logged for this day.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                  <table className="w-full min-w-[800px] border-collapse font-mono text-[0.7rem]">
                    <thead>
                      <tr className="border-b border-rule/60 text-left uppercase tracking-[0.1em] text-ink-mute">
                        <th className="px-2 py-1.5 font-normal">Time</th>
                        <th className="px-2 py-1.5 font-normal">Supplier</th>
                        <th className="px-2 py-1.5 font-normal">Cert / Contract</th>
                        <th className="px-2 py-1.5 font-normal">eRSV</th>
                        <th className="px-2 py-1.5 font-normal">C14</th>
                        <th className="px-2 py-1.5 font-normal">Loaded</th>
                        <th className="px-2 py-1.5 text-right font-normal">Total kg</th>
                        <th className="px-2 py-1.5 text-right font-normal">Veg % (T / M)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dayEntries.map((e) => {
                        const sup = supplierMap.get(e.supplier_id);
                        const cert =
                          e.certificate_id != null ? certificateMap.get(e.certificate_id) : null;
                        const contract =
                          e.contract_id != null ? contractMap.get(e.contract_id) : null;
                        const loaded = describeLoaded(e.car_kg, e.truck_kg, e.special_kg);
                        return (
                          <tr
                            key={e.id}
                            className="border-b border-rule/40 last:border-b-0 hover:bg-bg-soft/50"
                          >
                            <td className="px-2 py-1.5 text-ink">{fmtTime(e.entry_time)}</td>
                            <td className="px-2 py-1.5 text-ink">
                              {sup?.name ?? sup?.code ?? `#${e.supplier_id}`}
                            </td>
                            <td className="px-2 py-1.5 text-ink-soft">
                              <span className="block">{cert?.cert_number ?? '—'}</span>
                              <span className="block text-[0.62rem] text-ink-mute">
                                {contract?.code ?? '—'}
                              </span>
                            </td>
                            <td className="px-2 py-1.5 text-ink-soft">{e.ersv_number ?? '—'}</td>
                            <td className="px-2 py-1.5 text-ink-soft">
                              {e.c14_analysis || e.c14_value != null ? (
                                <>
                                  <span className="block">{e.c14_analysis ?? '—'}</span>
                                  {e.c14_value != null && (
                                    <span className="block text-[0.62rem] text-ink-mute tabular-nums">
                                      {fmtPct(e.c14_value)}
                                    </span>
                                  )}
                                </>
                              ) : (
                                '—'
                              )}
                            </td>
                            <td className="px-2 py-1.5 text-ink-soft">
                              {loaded.types.length === 0 ? (
                                '—'
                              ) : (
                                <span className="flex flex-wrap gap-1">
                                  {loaded.types.map((t) => (
                                    <span
                                      key={t.label}
                                      className="inline-flex items-center gap-1 border border-rule/60 bg-bg px-1.5 py-0.5 text-[0.6rem] uppercase tracking-[0.1em]"
                                    >
                                      <span className="text-ink-mute">{t.label}</span>
                                      <span className="tabular-nums text-ink">{fmtKg(t.value)}</span>
                                    </span>
                                  ))}
                                </span>
                              )}
                            </td>
                            <td className="px-2 py-1.5 text-right tabular-nums font-medium text-ink">
                              {fmtKg(e.total_input_kg)}
                            </td>
                            <td className="px-2 py-1.5 text-right tabular-nums text-ink-soft">
                              {fmtPct(e.theor_veg_pct)} / {fmtPct(e.manuf_veg_pct)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </section>
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

function BreakdownTile({
  label,
  value,
  unit,
}: {
  label: string;
  value: string | null | undefined;
  unit?: 'kg' | 'L';
}) {
  const u = unit ?? 'kg';
  return (
    <div className="border border-rule/60 bg-bg-soft px-2.5 py-2">
      <p className="text-[0.6rem] uppercase tracking-[0.12em] text-ink-mute">{label}</p>
      <p className="mt-1 tabular-nums text-ink">
        {fmtKg(value)}
        <span className="ml-1 text-[0.6rem] text-ink-mute">{u}</span>
      </p>
    </div>
  );
}
