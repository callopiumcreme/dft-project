const PROBLEMS = [
  {
    n: '01',
    title: 'Manual mass balance in Excel',
    body:
      'Closure errors compound across the month. By the time an auditor finds them, the certificate window is already open and the export contract is at risk.',
    tag: 'Excel · errors',
  },
  {
    n: '02',
    title: 'C14 lab disconnected from operations',
    body:
      'Sample IDs travel by email, results land in a PDF, and nobody can prove which lot was tested. The biogenic fraction floats in a parallel system.',
    tag: 'C14 · email',
  },
  {
    n: '03',
    title: 'POS documents rebuilt by hand',
    body:
      'Every shipment to the UK refinery means re-keying tonnage, supplier and certificate references into a Word template. Each version is a new compliance liability.',
    tag: 'POS · rework',
  },
];

export function Problem() {
  return (
    <section id="problem" className="relative">
      <div className="container-edit">
        <div className="border-t border-rule" />
        <div className="section-head">
          <div>
            <div className="eyebrow mb-4">§ 02 — The problem</div>
          </div>
          <div>
            <h2 className="text-balance text-[clamp(1.9rem,4.5vw,3.4rem)] font-light leading-[1.05]">
              Spreadsheets, lab PDFs and Word templates were never going to{' '}
              <em className="not-italic text-olive">survive an ISCC audit</em>.
            </h2>
            <p className="mt-6 max-w-reading text-pretty text-ink-soft text-lg leading-relaxed">
              Pyrolysis plants exporting to UK refineries operate under one of
              the strictest sustainability regimes in the world — RTFO and the
              UK Department for Transport. The tooling most plants run today
              was not built for it.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-rule mt-12 border border-rule">
          {PROBLEMS.map((p) => (
            <article
              key={p.n}
              className="bg-bg p-8 md:p-10 flex flex-col min-h-[340px]"
            >
              <div className="flex items-baseline justify-between mb-10">
                <span className="font-display text-4xl text-ink-mute tabular tracking-tightest">
                  {p.n}
                </span>
                <span className="eyebrow">{p.tag}</span>
              </div>
              <h3 className="text-2xl md:text-[1.7rem] font-light leading-tight text-balance mb-4">
                {p.title}
              </h3>
              <p className="text-ink-soft text-pretty leading-relaxed mt-auto">
                {p.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
