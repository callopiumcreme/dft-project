import { ArrowDownRight, ArrowUpRight } from 'lucide-react';

export function Hero() {
  return (
    <section className="relative pt-32 pb-24 md:pt-40 md:pb-32 overflow-hidden">
      {/* Document-style header line */}
      <div className="container-edit">
        <div className="flex items-center justify-between text-ink-mute mb-16 reveal" style={{ animationDelay: '0ms' }}>
          <div className="flex items-center gap-3 eyebrow">
            <span aria-hidden className="block w-6 h-px bg-rule" />
            <span>Doc · 01 / Edition 2026</span>
          </div>
          <div className="hidden sm:flex items-center gap-6 eyebrow">
            <span>04°18′N 74°48′W</span>
            <span>Girardot · CO</span>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-x-8 gap-y-16 items-end">
          {/* Headline column */}
          <div className="col-span-12 md:col-span-7">
            <h1
              className="reveal text-balance text-[clamp(2.6rem,7vw,5.6rem)] font-light"
              style={{ animationDelay: '120ms' }}
            >
              Mass balance,{' '}
              <em className="not-italic font-medium text-olive">
                certifiable.
              </em>
              <br />
              <span className="text-ink-soft">
                For the plants that turn{' '}
                <span className="italic font-light">end-of-life tyres</span>{' '}
                into refined pyrolysis oil for the UK market.
              </span>
            </h1>

            <p
              className="reveal mt-10 max-w-[52ch] text-pretty text-lg md:text-xl text-ink-soft leading-relaxed"
              style={{ animationDelay: '260ms' }}
            >
              ISCC EU and RED&nbsp;II compliant traceability for industrial pyrolysis.
              Load-by-load chain of custody, automatic mass-balance closure,
              third-party C14 sign-off and immutable audit logs — built for plants
              exporting to Crown Oil in the United Kingdom.
            </p>

            <div
              className="reveal mt-12 flex flex-wrap items-center gap-6"
              style={{ animationDelay: '400ms' }}
            >
              <a
                href="#contact"
                className="inline-flex items-center gap-3 bg-ink text-bg h-12 px-7 font-mono text-[0.78rem] uppercase tracking-[0.16em] hover:bg-olive-deep transition-colors"
              >
                Request a demo
                <ArrowUpRight className="h-4 w-4" strokeWidth={1.4} />
              </a>
              <a
                href="#stack"
                className="inline-flex items-center gap-2 font-mono text-[0.78rem] uppercase tracking-[0.16em] text-ink-soft hover:text-ink transition-colors border-b border-rule hover:border-ink pb-1.5"
              >
                Technical documentation
                <ArrowDownRight className="h-4 w-4" strokeWidth={1.4} />
              </a>
            </div>
          </div>

          {/* Right column: audit-style data card */}
          <div className="col-span-12 md:col-span-5 md:pl-8">
            <DashPreview />
          </div>
        </div>

        {/* Footnote-style strip */}
        <div className="mt-24 md:mt-32 border-t border-rule pt-5 grid grid-cols-2 md:grid-cols-4 gap-y-6 gap-x-8">
          {[
            { k: 'Standard', v: 'ISCC EU 205' },
            { k: 'Directive', v: 'EU 2018/2001' },
            { k: 'Lab partner', v: 'Saybolt NL · C14' },
            { k: 'Closure tol.', v: '0.5% configurable' },
          ].map((f, i) => (
            <div
              key={f.k}
              className="reveal"
              style={{ animationDelay: `${500 + i * 80}ms` }}
            >
              <div className="eyebrow mb-2">{f.k}</div>
              <div className="font-mono text-sm text-ink">{f.v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Decorative diagonal hairlines */}
      <svg
        aria-hidden
        className="absolute -top-32 -right-24 w-[480px] h-[480px] text-rule opacity-50 pointer-events-none"
        viewBox="0 0 480 480"
        fill="none"
      >
        {Array.from({ length: 12 }).map((_, i) => (
          <line
            key={i}
            x1={0}
            y1={i * 48}
            x2={480}
            y2={i * 48 - 240}
            stroke="currentColor"
            strokeWidth={0.5}
          />
        ))}
      </svg>
    </section>
  );
}

function DashPreview() {
  const rows = [
    { id: 'L-2025-0148', supplier: 'ESENTTIA', kg: '184,200', state: 'verified' },
    { id: 'L-2025-0147', supplier: 'LITOPLAS', kg: '92,860', state: 'verified' },
    { id: 'L-2025-0146', supplier: 'BIOWASTE', kg: '156,400', state: 'pending C14' },
    { id: 'L-2025-0145', supplier: 'ESENTTIA', kg: '210,500', state: 'verified' },
  ];

  return (
    <div
      className="reveal relative bg-bg-soft border border-rule p-7 md:p-8"
      style={{ animationDelay: '320ms' }}
    >
      {/* Stamp */}
      <span className="stamp absolute -top-3 right-6 bg-bg">
        <span className="block w-1.5 h-1.5 rounded-full bg-accent" />
        ISCC · audit ready
      </span>

      <div className="flex items-center justify-between mb-5">
        <div className="eyebrow">Live · January 2026</div>
        <div className="font-mono text-[0.7rem] text-ink-mute">07 May · 14:21 UTC</div>
      </div>

      {/* Mass balance closure indicator */}
      <div className="mb-7">
        <div className="flex items-baseline justify-between mb-2">
          <span className="eyebrow">Mass balance closure</span>
          <span className="tabular text-sm text-olive">99.74%</span>
        </div>
        <div className="h-px bg-rule relative overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 bg-olive"
            style={{ width: '99.74%', height: 2, top: -0.5 }}
          />
        </div>
        <div className="flex justify-between mt-1.5 font-mono text-[0.65rem] text-ink-mute">
          <span>0%</span>
          <span>tol. 0.5% ·</span>
          <span>100%</span>
        </div>
      </div>

      <div className="rule mb-5" />

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-y-5 gap-x-6 mb-7">
        <KPI label="Input · kg" value="643,960" />
        <KPI label="Output EU · kg" value="201,348" />
        <KPI label="Loads · MTD" value="48" />
        <KPI label="POS issued" value="12" />
      </div>

      <div className="rule mb-4" />

      {/* Loads table */}
      <div className="space-y-2">
        <div className="grid grid-cols-12 gap-2 eyebrow text-ink-mute pb-1">
          <span className="col-span-4">Load</span>
          <span className="col-span-4">Supplier</span>
          <span className="col-span-2 text-right">Kg</span>
          <span className="col-span-2 text-right">State</span>
        </div>
        {rows.map((r) => (
          <div
            key={r.id}
            className="grid grid-cols-12 gap-2 font-mono text-[0.78rem] text-ink py-1.5 border-t border-rule/60"
          >
            <span className="col-span-4 text-ink-soft">{r.id}</span>
            <span className="col-span-4">{r.supplier}</span>
            <span className="col-span-2 text-right tabular">{r.kg}</span>
            <span
              className={`col-span-2 text-right text-[0.65rem] uppercase tracking-[0.1em] ${
                r.state === 'verified' ? 'text-olive' : 'text-accent'
              }`}
            >
              {r.state}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function KPI({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="eyebrow mb-1.5">{label}</div>
      <div className="font-display text-3xl font-light tabular tracking-tightest text-ink">
        {value}
      </div>
    </div>
  );
}
