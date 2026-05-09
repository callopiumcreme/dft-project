import Link from 'next/link';

const COLS = [
  {
    title: 'Product',
    items: [
      { label: 'Mass balance', href: '#solution' },
      { label: 'Audit log', href: '#solution' },
      { label: 'POS documents', href: '#solution' },
      { label: 'C14 sign-off', href: '#solution' },
    ],
  },
  {
    title: 'Resources',
    items: [
      { label: 'Documentation', href: '/docs' },
      { label: 'Blog', href: '/blog' },
      { label: 'Case studies', href: '#case-study' },
      { label: 'Changelog', href: '/changelog' },
    ],
  },
  {
    title: 'Standards',
    items: [
      { label: 'ISCC EU', href: 'https://www.iscc-system.org/', external: true },
      { label: 'EU RED II', href: 'https://eur-lex.europa.eu/eli/dir/2018/2001/oj', external: true },
      { label: 'Mass balance approach', href: '#compliance' },
      { label: 'Compliance scope', href: '#compliance' },
    ],
  },
  {
    title: 'Company',
    items: [
      { label: 'About', href: '/about' },
      { label: 'Contact', href: '#contact' },
      { label: 'Privacy', href: '/privacy' },
      { label: 'Terms', href: '/terms' },
    ],
  },
];

export function Footer() {
  return (
    <footer className="relative pt-24 pb-12 border-t border-rule">
      <div className="container-edit">
        {/* Colophon */}
        <div className="grid grid-cols-12 gap-8 mb-20">
          <div className="col-span-12 md:col-span-4">
            <Link href="/" className="flex items-center gap-3 mb-6 w-fit">
              <span aria-hidden className="block w-2.5 h-2.5 rotate-45 bg-accent" />
              <span className="font-display text-2xl tracking-tightest">DFT</span>
              <span className="eyebrow">Pyrolysis traceability</span>
            </Link>
            <p className="max-w-[44ch] text-pretty text-ink-soft text-lg leading-relaxed font-display font-light">
              Mass balance, traceability and audit-grade documentation for
              industrial pyrolysis plants exporting biofuel under ISCC&nbsp;EU
              and RED&nbsp;II.
            </p>

            <Link
              href="/login"
              className="mt-8 inline-flex items-center gap-3 font-mono text-[0.78rem] uppercase tracking-[0.16em] border border-ink px-5 h-10 hover:bg-ink hover:text-bg transition-colors"
            >
              Sign in to the app →
            </Link>
          </div>

          {COLS.map((col) => (
            <div key={col.title} className="col-span-6 md:col-span-2">
              <div className="eyebrow mb-5">{col.title}</div>
              <ul className="space-y-3">
                {col.items.map((it) => (
                  <li key={it.label}>
                    <Link
                      href={it.href}
                      target={'external' in it && it.external ? '_blank' : undefined}
                      rel={'external' in it && it.external ? 'noopener noreferrer' : undefined}
                      className="text-ink-soft hover:text-olive transition-colors"
                    >
                      {it.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar — colophon style */}
        <div className="border-t border-rule pt-8 flex flex-col md:flex-row md:items-center md:justify-between gap-6 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
          <div className="flex flex-wrap gap-x-8 gap-y-2">
            <span>© {new Date().getFullYear()} DFT Project</span>
            <span>All rights reserved</span>
            <span>Made for plants exporting to EU refineries</span>
          </div>
          <div className="flex items-center gap-6">
            <span>Tenerife · ES</span>
            <span aria-hidden className="block w-1 h-1 rounded-full bg-rule" />
            <span>Girardot · CO</span>
            <span aria-hidden className="block w-1 h-1 rounded-full bg-rule" />
            <span>v0.1 · Edition 2026</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
