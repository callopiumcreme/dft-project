const STACK = [
  {
    layer: 'Frontend',
    items: ['Next.js 14 · App Router', 'TypeScript', 'Tailwind · shadcn/ui', 'TanStack Table & Query'],
  },
  {
    layer: 'Backend',
    items: ['FastAPI 0.111', 'Python 3.12', 'SQLAlchemy 2.0', 'WeasyPrint · POS PDF'],
  },
  {
    layer: 'Data',
    items: ['PostgreSQL 16', 'Append-only audit ledger', 'SHA-256 hash chain', 'pgvector ready'],
  },
  {
    layer: 'Auth & Audit',
    items: ['NextAuth · 4 roles', 'Admin · Operator · Certifier · Viewer', 'Hash-verified commits', 'Immutable POS post-signature'],
  },
];

export function Stack() {
  return (
    <section id="stack" className="relative bg-bg-deep text-bg py-24 md:py-32 overflow-hidden">
      {/* Subtle grid pattern */}
      <svg
        aria-hidden
        className="absolute inset-0 w-full h-full opacity-[0.04] pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
            <path d="M 48 0 L 0 0 0 48" fill="none" stroke="currentColor" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      <div className="container-edit relative">
        <div className="section-head !pt-0">
          <div>
            <div className="eyebrow mb-4 !text-[#A39A82]">§ 05 — Stack</div>
          </div>
          <div>
            <h2 className="text-balance text-[clamp(1.9rem,4.5vw,3.4rem)] font-light leading-[1.05] !text-bg">
              Open-source. Self-hosted or managed.{' '}
              <em className="not-italic" style={{ color: 'var(--olive-soft)' }}>
                Yours to inspect.
              </em>
            </h2>
            <p className="mt-6 max-w-reading text-pretty text-[#C9C2B0] text-lg leading-relaxed">
              No closed black box between your operators and an EU auditor. The
              data model, the audit log, the document templates — all readable,
              versioned, deployable on infrastructure you control.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px" style={{ background: '#33312A' }}>
          {STACK.map((s) => (
            <div key={s.layer} className="bg-bg-deep p-8">
              <div className="flex items-baseline justify-between mb-5 pb-3 border-b" style={{ borderColor: '#33312A' }}>
                <span className="font-mono text-[0.72rem] uppercase tracking-[0.16em]" style={{ color: '#A39A82' }}>
                  {s.layer}
                </span>
              </div>
              <ul className="space-y-3">
                {s.items.map((it) => (
                  <li
                    key={it}
                    className="font-mono text-[0.85rem] text-bg leading-relaxed flex items-start gap-2.5"
                  >
                    <span aria-hidden style={{ color: 'var(--olive-soft)' }} className="select-none">
                      ›
                    </span>
                    <span>{it}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-wrap items-center gap-x-12 gap-y-4 font-mono text-[0.72rem] uppercase tracking-[0.16em]" style={{ color: '#A39A82' }}>
          <span>· Apache 2.0</span>
          <span>· REST API</span>
          <span>· Docker compose</span>
          <span>· Hetzner / AWS / GCP</span>
          <span>· 2–4 week deployment</span>
        </div>
      </div>
    </section>
  );
}
