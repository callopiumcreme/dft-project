import { ShieldCheck, FileCheck, ScrollText, GanttChart } from 'lucide-react';

const BADGES = [
  {
    name: 'ISCC EU',
    sub: 'Sustainability certification scheme',
    icon: ShieldCheck,
  },
  {
    name: 'EU RED II',
    sub: 'Directive 2018/2001',
    icon: FileCheck,
  },
  {
    name: 'Mass balance',
    sub: 'Chain of custody',
    icon: GanttChart,
  },
  {
    name: 'POS · audit',
    sub: 'Proof of sustainability',
    icon: ScrollText,
  },
];

export function Compliance() {
  return (
    <section id="compliance" className="relative py-24 md:py-32">
      <div className="container-edit">
        <div className="section-head">
          <div>
            <div className="eyebrow mb-4">§ 04 — Compliance</div>
          </div>
          <div>
            <h2 className="text-balance text-[clamp(1.9rem,4.5vw,3.4rem)] font-light leading-[1.05]">
              Built to stand up to the{' '}
              <em className="not-italic text-olive">certifier in the room</em>.
            </h2>
            <p className="mt-6 max-w-reading text-pretty text-ink-soft text-lg leading-relaxed">
              Schema, audit log and document model are designed against the
              ISCC EU System Document 205 and Directive 2018/2001. Closure
              tolerance, retention and signature workflows are configured in
              code, not in policy memos.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-rule border border-rule">
          {BADGES.map((b) => (
            <div
              key={b.name}
              className="bg-bg p-8 md:p-10 flex flex-col items-start gap-6 group"
            >
              <div className="relative">
                <span className="absolute -inset-3 border border-accent/30 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                <b.icon
                  className="h-9 w-9 text-accent relative"
                  strokeWidth={1.1}
                />
              </div>
              <div>
                <div className="font-display text-2xl tracking-tightest mb-1">
                  {b.name}
                </div>
                <div className="font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-mute">
                  {b.sub}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col md:flex-row md:items-end md:justify-between gap-6 border-t border-rule pt-8">
          <p className="font-display text-2xl md:text-3xl font-light tracking-editorial max-w-[28ch] text-pretty">
            Ready for certifier audit on day one.
          </p>
          <a
            href="#contact"
            className="font-mono text-[0.78rem] uppercase tracking-[0.16em] border-b border-ink hover:border-olive hover:text-olive pb-1.5 transition-colors w-fit"
          >
            Speak to our compliance lead →
          </a>
        </div>
      </div>
    </section>
  );
}
