import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { apiGet, ApiError, SESSION_COOKIE } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { welcomePathFor } from '@/config/welcome-routing';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

const INFO_ROWS: Array<{ category: string; details: string }> = [
  {
    category: 'Transaction Records',
    details:
      'JLY purchase-order + OIS invoice references, dates, quantities, ISO containers. Commercial pricing intentionally excluded — out of audit scope.',
  },
  {
    category: 'Mass Balance Data',
    details:
      'ISCC EU pooled-tank mass-balance ledger, full chain of custody January through August 2025.',
  },
  {
    category: 'Sustainability Certificates',
    details:
      'ISCC EU supplier certificates and OisteBio Girardot (Colombia) site certification.',
  },
  {
    category: 'Shipping Documents',
    details:
      'Outbound shipping documents from Girardot (Colombia) through to delivery in Bury (UK), with container, vessel and road-delivery references.',
  },
  {
    category: 'Delivery Details',
    details:
      'DEL-CRW-2025-2 — 500,410 kg DEV-P100, DAP Bury (UK) 2025-08-15, invoice group JLY001–JLY020.',
  },
];

const FIND_BULLETS: string[] = [
  'Production records and pooled-tank mass-balance ledger for January–August 2025.',
  'Full traceability of DEL-CRW-2025-2 from Girardot feedstock to Bury (UK) delivery.',
  'ISCC EU audit-ready exports, structured to support Crown Oil Ltd’s UK RTFO submission.',
  'DEV-P200 byproduct sales to Conquer Trade — segregated from the DEV-P100 chain.',
];

export default async function WelcomePage() {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) redirect('/login');

  let user: UserRead;
  try {
    user = await apiGet<UserRead>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    throw e;
  }

  if (!welcomePathFor(user.email)) redirect('/app');

  return (
    <div className="mx-auto max-w-editorial space-y-10">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Welcome
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          OisteBio audit access portal — UK DfT investigation
        </h1>
        <p className="mt-4 max-w-reading text-ink">
          Dear Ms Deeba Rehman,
        </p>
        <p className="mt-3 max-w-reading text-ink-soft">
          Welcome to OisteBio’s audit access portal for the UK DfT investigation
          into our 2025 supplies to Crown Oil Ltd. This platform provides
          complete transparency over our DEV-P100 renewable pyrolysis-oil
          production records and the chain of custody supporting Crown Oil’s
          UK RTFO submission for consignment DEL-CRW-2025-2.
        </p>
      </header>

      <section>
        <h2 className="font-display text-2xl tracking-editorial text-ink">
          Audit window in scope
        </h2>
        <p className="mt-3 max-w-reading text-ink-soft">
          OisteBio Girardot (Colombia) renewable pyrolysis-oil production,
          January through August 2025, operating under a pooled-tank
          mass-balance model (ISCC EU). The consignment under investigation is{' '}
          <span className="font-mono text-ink">DEL-CRW-2025-2</span> — 500,410
          kg DEV-P100, delivered DAP Bury (UK) 2025-08-15 via invoice group{' '}
          <span className="font-mono text-ink">JLY001–JLY020</span>.
        </p>
        <p className="mt-3 max-w-reading text-ink-soft">
          The earlier consignment{' '}
          <span className="font-mono text-ink">DEL-CRW-2025-1</span> pre-dates
          OisteBio’s current Fuel Management System v1.0 and falls outside the
          current investigation scope, as previously confirmed in audit
          communications.
        </p>
      </section>

      <section className="border border-rule bg-bg-soft px-6 py-5">
        <h2 className="font-display text-2xl tracking-editorial text-ink">
          Curated audit evidence bundle
        </h2>
        <p className="mt-3 max-w-reading text-ink-soft">
          We are pleased to provide a complete audit-ready bundle gathering
          all key documents subject to this investigation, together with
          navigation guides for our management system, to better facilitate
          your review work.
        </p>
        <p className="mt-2 max-w-reading text-ink-soft">
          The bundle mirrors the eight-point evidence structure of your
          request of 13 May 2026, and includes one short navigation guide per
          point cross-referencing every static record to its live counterpart
          in this system.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-4">
          <a
            href="/audit/DfT_Audit_Submission.zip"
            download
            className="inline-flex items-center gap-2 border border-ink bg-ink px-4 py-2 font-mono text-[0.78rem] uppercase tracking-[0.10em] text-bg hover:bg-ink-soft"
          >
            <span aria-hidden="true">↓</span>
            Download audit bundle (ZIP)
          </a>
          <span className="font-mono text-[0.72rem] uppercase tracking-[0.10em] text-ink-mute">
            ~8.7&nbsp;MB · 9 guides · 26 files
          </span>
        </div>
      </section>

      <section>
        <h2 className="font-display text-2xl tracking-editorial text-ink">
          What you can find here
        </h2>

        <div className="mt-6 overflow-x-auto border border-rule">
          <table className="w-full border-collapse text-left">
            <thead className="bg-bg-soft">
              <tr>
                <th
                  scope="col"
                  className="border-b border-rule px-4 py-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute"
                >
                  Information Category
                </th>
                <th
                  scope="col"
                  className="border-b border-rule px-4 py-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute"
                >
                  Details Available
                </th>
              </tr>
            </thead>
            <tbody>
              {INFO_ROWS.map((row) => (
                <tr key={row.category} className="align-top">
                  <td className="border-b border-rule px-4 py-3 font-mono text-[0.78rem] uppercase tracking-[0.10em] text-ink">
                    {row.category}
                  </td>
                  <td className="border-b border-rule px-4 py-3 text-ink-soft">
                    {row.details}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <ul className="mt-6 max-w-reading list-disc space-y-2 pl-5 text-ink-soft">
          {FIND_BULLETS.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl tracking-editorial text-ink">
          Getting started
        </h2>
        <p className="mt-3 max-w-reading text-ink-soft">
          Navigate the system modules to inspect production records, download
          supplier ISCC EU certificates, shipping documents from Girardot to
          Bury, and commercial invoice references. All modules mirror the
          eight-point evidence request received 13 May 2026.
        </p>
        <p className="mt-4 max-w-reading text-ink-soft">
          Should you require any assistance navigating the system or additional
          documentation, please contact our compliance team:{' '}
          <a
            href="mailto:export@oistebio.ch"
            className="font-mono text-ink underline decoration-rule underline-offset-4 hover:decoration-ink"
          >
            export@oistebio.ch
          </a>
        </p>
      </section>
    </div>
  );
}
