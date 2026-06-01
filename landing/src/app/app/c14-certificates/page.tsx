import { apiGet, ApiError } from '@/lib/api';
import type { C14CertificateDetail } from '@/lib/c14-certificate-client';
import { C14CertificateLink } from '@/components/c14-certificates/c14-certificate-link';
import { C14CertificateModalProvider } from '@/components/c14-certificates/c14-certificate-modal-provider';
import { UmamiViewEvent } from '@/components/analytics/umami-view-event';

export const dynamic = 'force-dynamic';

const monthFmt = new Intl.DateTimeFormat('en-GB', { month: 'short', year: 'numeric' });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtMonth(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return monthFmt.format(d);
}

function fmtPct(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return n.toFixed(2);
}

interface PageProps {
  searchParams: {
    active?: string;
  };
}

export default async function C14CertificatesPage({ searchParams }: PageProps) {
  const showAll = searchParams.active === 'all';

  let rows: C14CertificateDetail[] = [];
  let fetchError: string | null = null;

  try {
    rows = await apiGet<C14CertificateDetail[]>('/c14-certificates', {
      query: {
        ...(showAll ? { include_deleted: true } : {}),
      },
    });
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const pcts = rows
    .map((r) => Number(r.bio_carbon_pct))
    .filter((n) => Number.isFinite(n));
  const avgPct = pcts.length
    ? pcts.reduce((s, n) => s + n, 0) / pcts.length
    : null;

  return (
    <C14CertificateModalProvider>
      <div className="mx-auto max-w-editorial">
        <UmamiViewEvent
          name="view_c14_certificates_list"
          data={{ ...(showAll ? { include_deleted: true } : {}) }}
        />
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            Operations · FMS Appendix A
          </p>
          <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
            C14 certificates log
          </h1>
          <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
            {rows.length} radiocarbon certificate{rows.length === 1 ? '' : 's'}
            {showAll ? ' · deleted included' : ' · active only'}
            {' · bio-based carbon content (EN 16640 Annex B) of DEV-P100'}
          </p>
        </header>

        <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
          <nav className="flex gap-1 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
            <a
              href="/app/c14-certificates"
              className={
                !showAll
                  ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                  : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
              }
            >
              Active
            </a>
            <a
              href="/app/c14-certificates?active=all"
              className={
                showAll
                  ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                  : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
              }
            >
              All
            </a>
          </nav>
        </section>

        {fetchError && (
          <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
            Loading error: {fetchError}
          </div>
        )}

        <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <KpiTile label="Certificates" value={String(rows.length)} />
          <KpiTile
            label="Avg bio-based carbon"
            value={avgPct === null ? '—' : `${avgPct.toFixed(2)} %`}
          />
        </section>

        <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
          <table className="w-full border-collapse font-mono text-[0.72rem]">
            <thead className="border-b border-rule bg-bg">
              <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                <Th>Cert number</Th>
                <Th>Month</Th>
                <Th>Lab</Th>
                <Th>Sampled</Th>
                <Th>Tested</Th>
                <ThNum>Bio-C %</ThNum>
                <Th>SD link</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && !fetchError && (
                <tr>
                  <td colSpan={8} className="px-3 py-6 text-center text-ink-mute">
                    No C14 certificates match the selected filter.
                  </td>
                </tr>
              )}
              {rows.map((r) => {
                const deleted = !!r.deleted_at;
                return (
                  <tr
                    key={r.id}
                    className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                  >
                    <Td className="text-ink">
                      <C14CertificateLink c14Id={r.id} certNumber={r.cert_number} />
                    </Td>
                    <Td className="text-ink-soft">{fmtMonth(r.period_month)}</Td>
                    <Td className="text-ink-soft">{r.lab ?? '—'}</Td>
                    <Td className="text-ink-soft">{fmtDate(r.sampled_date)}</Td>
                    <Td className="text-ink-soft">{fmtDate(r.tested_date)}</Td>
                    <TdNum>{fmtPct(r.bio_carbon_pct)}</TdNum>
                    <Td className="text-ink-soft">{r.sustainability_decl ?? '—'}</Td>
                    <Td>
                      {deleted ? (
                        <span className="inline-block border border-accent bg-accent/5 px-2 py-0.5 text-[0.65rem] uppercase text-accent">
                          deleted
                        </span>
                      ) : (
                        <span className="inline-block border border-olive-deep bg-olive-deep/10 px-2 py-0.5 text-[0.65rem] uppercase text-olive-deep">
                          active
                        </span>
                      )}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      </div>
    </C14CertificateModalProvider>
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
