import { ScanLine, GitBranch, FlaskConical, Lock } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type Feature = {
  k: string;
  title: string;
  body: string;
  icon: LucideIcon;
  meta: string[];
};

const FEATURES: Feature[] = [
  {
    k: '01',
    title: 'Load-by-load chain of custody',
    body:
      'Every truck that arrives is a structured record: timestamp, supplier, transport class, certificate, eRSV and POS reference. Searchable, exportable, immutable.',
    icon: ScanLine,
    meta: ['CAR · TRUCK · SPECIAL', 'eRSV linked', 'POS attached'],
  },
  {
    k: '02',
    title: 'Automatic mass-balance closure',
    body:
      'Daily production splits into EU PROD, PLUS PROD, Carbon Black, Metal scrap, H₂O, Gas/Syngas and losses. Monthly and annual closure runs against a configurable tolerance — alerts fire before the auditor arrives.',
    icon: GitBranch,
    meta: ['Closure tol. 0.5%', 'Drill-down enabled', 'YE & monthly'],
  },
  {
    k: '03',
    title: 'Third-party C14 sign-off',
    body:
      'Saybolt NL — or any accredited lab — uploads results directly against the lot. Only certifier accounts can mark a batch as verified. No more PDFs in inboxes.',
    icon: FlaskConical,
    meta: ['Saybolt NL ready', 'Multi-lab capable', 'Digital sign-off'],
  },
  {
    k: '04',
    title: 'Append-only audit log',
    body:
      'Every certified record is hash-chained. POS documents are immutable post-signature. Operators cannot edit history; auditors cannot doubt it.',
    icon: Lock,
    meta: ['SHA-256 chain', 'No UPDATE / DELETE', 'ISCC ready'],
  },
];

export function Solution() {
  return (
    <section id="solution" className="relative bg-bg-soft mt-24 py-24 md:py-32">
      <div className="container-edit">
        <div className="section-head !pt-0">
          <div>
            <div className="eyebrow mb-4">§ 03 — The solution</div>
          </div>
          <div>
            <h2 className="text-balance text-[clamp(1.9rem,4.5vw,3.4rem)] font-light leading-[1.05]">
              One system from{' '}
              <em className="not-italic text-olive">truck</em> to{' '}
              <em className="not-italic text-olive">refinery</em>.
            </h2>
            <p className="mt-6 max-w-reading text-pretty text-ink-soft text-lg leading-relaxed">
              DFT replaces the spreadsheets, lab inboxes and Word templates with
              a single audit-grade record of every kilogram, from intake to
              export.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-rule border border-rule">
          {FEATURES.map((f) => (
            <article
              key={f.k}
              className="bg-bg-soft p-8 md:p-12 flex flex-col gap-6 min-h-[360px]"
            >
              <div className="flex items-start justify-between gap-6">
                <span className="font-mono text-[0.78rem] tracking-[0.18em] uppercase text-ink-mute">
                  Feature · {f.k}
                </span>
                <f.icon
                  className="h-6 w-6 text-olive shrink-0"
                  strokeWidth={1.2}
                />
              </div>

              <h3 className="text-balance text-3xl md:text-[2rem] font-light leading-[1.1] max-w-[22ch]">
                {f.title}
              </h3>

              <p className="text-ink-soft leading-relaxed text-pretty max-w-reading">
                {f.body}
              </p>

              <div className="flex flex-wrap gap-x-4 gap-y-2 mt-auto pt-4 border-t border-rule">
                {f.meta.map((m) => (
                  <span
                    key={m}
                    className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute"
                  >
                    · {m}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
