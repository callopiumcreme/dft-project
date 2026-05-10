'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';

const LABELS: Record<string, string> = {
  app: 'Dashboard',
  reports: 'Reports',
  'mass-balance': 'Mass balance',
  'by-supplier': 'By supplier',
  'closure-status': 'Closure',
  suppliers: 'Suppliers',
  certificates: 'Certificates',
  contracts: 'Contracts',
  users: 'Users',
  new: 'New',
  edit: 'Edit',
};

export function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);
  if (segments.length === 0) return null;

  const crumbs = segments.map((seg, i) => {
    const href = '/' + segments.slice(0, i + 1).join('/');
    const label = LABELS[seg] ?? seg;
    return { href, label };
  });

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
      {crumbs.map((c, i) => {
        const last = i === crumbs.length - 1;
        return (
          <span key={c.href} className="flex items-center gap-1.5">
            {i > 0 && <ChevronRight className="h-3 w-3" aria-hidden />}
            {last ? (
              <span className="text-ink">{c.label}</span>
            ) : (
              <Link href={c.href} className="hover:text-ink transition-colors">
                {c.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
