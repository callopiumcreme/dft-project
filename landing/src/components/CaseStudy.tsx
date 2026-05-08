const FIGURES = [
  {
    label: 'Total input · 2024',
    value: '8,011,725',
    unit: 'kg',
    note: 'Mixed plastic · ESENTTIA · LITOPLAS · BIOWASTE',
  },
  {
    label: 'EU PROD',
    value: '2,475,623',
    unit: 'kg',
    note: 'Compliant export · pre-C14',
  },
  {
    label: 'PLUS PROD',
    value: '2,972,349',
    unit: 'kg',
    note: 'Premium grade output',
  },
  {
    label: 'Output EU certified',
    value: '2,563,752',
    unit: 'kg',
    note: 'Post-C14 · refinery-bound',
    accent: true,
  },
];

export function CaseStudy() {
  return (
    <section id="case-study" className="relative py-24 md:py-32">
      <div className="container-edit">
        <div className="section-head">
          <div>
            <div className="eyebrow mb-4">§ 06 — Case study</div>
            <div className="font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-mute mt-3">
              Girardot · Cundinamarca · CO
            </div>
          </div>
          <div>
            <h2 className="text-balance text-[clamp(1.9rem,4.5vw,3.4rem)] font-light leading-[1.05]">
              Eight million kilograms of mixed plastic.{' '}
              <em className="not-italic text-olive">One ledger.</em>
            </h2>
            <p className="mt-6 max-w-reading text-pretty text-ink-soft text-lg leading-relaxed">
              The BiNova plant in Girardot, Colombia, processes mixed plastic
              waste into pyrolytic oil destined for European refineries.
              In year-end 2024, every load, every production batch and every
              gram exported was reconciled against the ISCC mass-balance.
            </p>
          </div>
        </div>

        {/* Figure stack */}
        <div className="border-y border-rule">
          {FIGURES.map((f, i) => (
            <div
              key={f.label}
              className="grid grid-cols-12 gap-4 md:gap-8 py-8 md:py-10 border-b last:border-b-0 border-rule items-baseline group"
            >
              <div className="col-span-12 md:col-span-3">
                <div className="eyebrow mb-2">
                  {String(i + 1).padStart(2, '0')} · {f.label}
                </div>
              </div>
              <div className="col-span-9 md:col-span-6">
                <div className="flex items-baseline gap-3 md:gap-5">
                  <span
                    className={`megafig text-[clamp(2.8rem,8vw,6.5rem)] ${
                      f.accent ? 'text-accent' : 'text-ink'
                    }`}
                  >
                    {f.value}
                  </span>
                  <span className="font-mono text-base md:text-lg text-ink-mute">
                    {f.unit}
                  </span>
                </div>
              </div>
              <div className="col-span-3 md:col-span-3">
                <div className="font-mono text-[0.7rem] md:text-[0.75rem] uppercase tracking-[0.14em] text-ink-mute md:text-right text-pretty">
                  {f.note}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <blockquote className="max-w-[44ch] text-pretty">
            <p className="font-display text-xl md:text-2xl italic font-light leading-snug text-ink-soft">
              &ldquo;The auditor opened a tablet, queried any month of 2024, and
              the numbers reconciled in seconds. That conversation used to take
              days.&rdquo;
            </p>
            <footer className="mt-4 eyebrow">
              BiNova · plant operations · 2025
            </footer>
          </blockquote>
          <a
            href="#contact"
            className="font-mono text-[0.78rem] uppercase tracking-[0.16em] border-b border-ink hover:border-olive hover:text-olive pb-1.5 transition-colors w-fit"
          >
            Read the full case (PDF) →
          </a>
        </div>
      </div>
    </section>
  );
}
