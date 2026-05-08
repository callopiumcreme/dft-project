const TIERS = [
  {
    name: 'Pilot',
    price: 'Contact',
    sub: 'Up to 1 plant · 6-month evaluation',
    features: [
      'Full feature set',
      'Supplier seed + roles',
      'POS document generation',
      'C14 lab integration · 1 partner',
      'Email support',
    ],
    cta: 'Start a pilot',
  },
  {
    name: 'Production',
    price: 'Contact',
    sub: 'Single plant · ISCC audit-ready',
    features: [
      'Everything in Pilot',
      'Custom mass-balance tolerances',
      'Multi-lab certifier support',
      'On-call audit assistance',
      'SLA · 99.5%',
    ],
    cta: 'Plan a deployment',
    highlight: true,
  },
  {
    name: 'Multi-plant',
    price: 'Roadmap',
    sub: '2026 — multi-site consolidation',
    features: [
      'Centralised dashboards',
      'Cross-plant mass balance',
      'Per-plant audit logs',
      'API consolidation',
      'Dedicated CSM',
    ],
    cta: 'Join the waitlist',
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="relative py-24 md:py-32 bg-bg-soft">
      <div className="container-edit">
        <div className="section-head !pt-0">
          <div>
            <div className="eyebrow mb-4">§ 07 — Engagement</div>
          </div>
          <div>
            <h2 className="text-balance text-[clamp(1.9rem,4.5vw,3.4rem)] font-light leading-[1.05]">
              Priced{' '}
              <em className="not-italic text-olive">per plant</em>, not per
              user.
            </h2>
            <p className="mt-6 max-w-reading text-pretty text-ink-soft text-lg leading-relaxed">
              Operators, certifiers and refinery viewers come and go. Your
              license tracks the asset, not the headcount. Final figures depend
              on volume, lab partners and deployment topology — we put numbers
              on the table after a 30-minute scoping call.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-rule border border-rule">
          {TIERS.map((t) => (
            <article
              key={t.name}
              className={`p-8 md:p-10 flex flex-col gap-6 ${
                t.highlight ? 'bg-bg' : 'bg-bg-soft'
              }`}
            >
              <div className="flex items-baseline justify-between">
                <h3 className="font-display text-3xl tracking-tightest font-light">
                  {t.name}
                </h3>
                {t.highlight && (
                  <span className="stamp">
                    <span className="block w-1.5 h-1.5 rounded-full bg-accent" />
                    Recommended
                  </span>
                )}
              </div>
              <div>
                <div className="font-display text-4xl font-light tracking-tightest text-ink">
                  {t.price}
                </div>
                <div className="font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-mute mt-2">
                  {t.sub}
                </div>
              </div>
              <ul className="space-y-3 mt-2 border-t border-rule pt-5">
                {t.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2.5 text-ink-soft text-pretty"
                  >
                    <span aria-hidden className="text-olive select-none mt-0.5">
                      ›
                    </span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <a
                href="#contact"
                className={`mt-auto inline-flex items-center justify-center font-mono text-[0.78rem] uppercase tracking-[0.16em] h-11 px-5 transition-colors border ${
                  t.highlight
                    ? 'bg-ink text-bg border-ink hover:bg-olive-deep hover:border-olive-deep'
                    : 'bg-transparent text-ink border-ink hover:bg-ink hover:text-bg'
                }`}
              >
                {t.cta}
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
