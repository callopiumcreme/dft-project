import { redirect } from 'next/navigation';
import { Card } from '@/components/ui/card';
import {
  WINDOW_START_ISO as PERIOD_FROM,
  WINDOW_END_ISO as PERIOD_TO,
} from '@/config/paper-records-window';
import { welcomePathFor } from '@/config/welcome-routing';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { Sparkline, type SparkPoint } from './_components/sparkline';

type DailyRow = components['schemas']['MassBalanceDailyRow'];
type ClosureRow = components['schemas']['ClosureStatusRow'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const pctFmt = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function toNum(v: string | null | undefined): number {
  if (v === null || v === undefined) return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

async function safeFetch<T>(path: string, query?: Record<string, string | number>): Promise<T | null> {
  try {
    return await apiGet<T>(path, { query });
  } catch (e) {
    if (e instanceof ApiError) {
      console.error(`[dashboard] ${path} failed:`, e.status, e.detail);
      return null;
    }
    throw e;
  }
}

// PERIOD_FROM / PERIOD_TO are now imported from `@/config/paper-records-window`
// (formerly `WINDOW_START_ISO` / `WINDOW_END_ISO`). The dashboard scope
// is bound to the disclosure window so a single edit there reshapes every
// surface at once — see file header in paper-records-window.ts (N1 / N6).

export default async function AppHomePage() {
  // Per-user welcome routing: if /auth/me email matches an entry in
  // WELCOME_ROUTING, send the user there instead of rendering the default
  // dashboard. Deep links (e.g. /app/logistics) bypass this branch.
  let welcome: string | null = null;
  try {
    const me = await apiGet<UserRead>('/auth/me');
    welcome = welcomePathFor(me.email);
  } catch (e) {
    if (!(e instanceof ApiError)) throw e;
    // 401 → layout already redirects to /login.
  }
  if (welcome) redirect(welcome);

  const [daily, closure] = await Promise.all([
    safeFetch<DailyRow[]>('/reports/mass-balance/daily', {
      date_from: PERIOD_FROM,
      date_to: PERIOD_TO,
    }),
    safeFetch<ClosureRow[]>('/reports/closure-status'),
  ]);

  const dailyRows = daily ?? [];
  const closureRows = closure ?? [];
  const fetchFailed = daily === null || closure === null;

  const sortedDaily = [...dailyRows].sort((a, b) => a.day.localeCompare(b.day));

  const totalInput = sortedDaily.reduce((s, r) => s + toNum(r.input_total_kg), 0);
  const totalOutput = sortedDaily.reduce((s, r) => s + toNum(r.output_total_kg), 0);

  const closureValues = sortedDaily
    .filter((r) => r.closure_diff_pct !== null && r.closure_diff_pct !== undefined)
    .map((r) => toNum(r.closure_diff_pct));
  const avgClosure =
    closureValues.length > 0
      ? closureValues.reduce((s, v) => s + v, 0) / closureValues.length
      : 0;

  const alertCount = closureRows.filter((r) => r.bucket === 'alert').length;

  const sparkData: SparkPoint[] = sortedDaily.map((r) => ({
    day: r.day,
    input: toNum(r.input_total_kg),
    output: toNum(r.output_total_kg),
  }));

  const lastDay = sortedDaily[sortedDaily.length - 1]?.day;
  const firstDay = sortedDaily[0]?.day;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Overview
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Dashboard</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Mass balance KPI — RTFO audit window
          {firstDay && lastDay ? ` (${firstDay} → ${lastDay})` : ' (Jan – Aug 2025)'} · {sortedDaily.length} days.
        </p>
        {fetchFailed && (
          <p className="mt-3 inline-block border border-rule bg-bg-soft px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
            Backend unreachable · partial data
          </p>
        )}
      </header>

      <section className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total input" value={`${numFmt.format(totalInput)} kg`} />
        <KpiCard label="Total output" value={`${numFmt.format(totalOutput)} kg`} />
        <KpiCard
          label="Avg closure"
          value={`${pctFmt.format(avgClosure)} %`}
          hint={closureValues.length === 0 ? 'No data' : `${closureValues.length} days`}
        />
        <KpiCard
          label="Closure alerts"
          value={numFmt.format(alertCount)}
          hint={`of ${closureRows.length} days`}
          tone={alertCount > 0 ? 'alert' : 'neutral'}
        />
      </section>

      <section className="mt-10 border border-rule bg-bg-soft p-5">
        <div className="flex items-baseline justify-between">
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
            Input vs output trend
          </p>
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
            kg / day
          </p>
        </div>
        <div className="mt-3">
          <Sparkline data={sparkData} />
        </div>
        <div className="mt-3 flex gap-4 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
          <span className="flex items-center gap-2">
            <span className="inline-block h-[2px] w-4 bg-olive-deep" /> Input
          </span>
          <span className="flex items-center gap-2">
            <span className="inline-block h-[2px] w-4 border-t border-dashed border-olive" /> Output
          </span>
        </div>
      </section>
    </div>
  );
}

function KpiCard({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: 'neutral' | 'alert';
}) {
  return (
    <Card className="p-5">
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">{label}</p>
      <p
        className={
          tone === 'alert'
            ? 'mt-3 font-display text-3xl tracking-editorial text-accent'
            : 'mt-3 font-display text-3xl tracking-editorial text-ink'
        }
      >
        {value}
      </p>
      <p className="mt-2 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
        {hint ?? 'Jan – Aug 2025'}
      </p>
    </Card>
  );
}
