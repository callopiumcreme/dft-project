'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Scale,
  Users,
  Award,
  FileText,
  type LucideIcon,
} from 'lucide-react';

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  group?: string;
};

const NAV: NavItem[] = [
  { href: '/app', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/app/reports/mass-balance', label: 'Mass balance', icon: Scale, group: 'Report' },
  { href: '/app/reports/by-supplier', label: 'Per fornitore', icon: Users, group: 'Report' },
  { href: '/app/reports/closure-status', label: 'Chiusura giornaliera', icon: Scale, group: 'Report' },
  { href: '/app/suppliers', label: 'Fornitori', icon: Users, group: 'Anagrafiche' },
  { href: '/app/certificates', label: 'Certificati', icon: Award, group: 'Anagrafiche' },
  { href: '/app/contracts', label: 'Contratti', icon: FileText, group: 'Anagrafiche' },
];

function isActive(pathname: string, href: string): boolean {
  if (href === '/app') return pathname === '/app';
  return pathname === href || pathname.startsWith(href + '/');
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  const groups = NAV.reduce<Record<string, NavItem[]>>((acc, item) => {
    const key = item.group ?? '';
    (acc[key] ||= []).push(item);
    return acc;
  }, {});

  return (
    <nav className="flex flex-col gap-8 px-6 py-8">
      {Object.entries(groups).map(([group, items]) => (
        <div key={group} className="flex flex-col gap-1">
          {group && (
            <p className="mb-2 px-2 font-mono text-[0.65rem] uppercase tracking-[0.18em] text-ink-mute">
              {group}
            </p>
          )}
          {items.map(({ href, label, icon: Icon }) => {
            const active = isActive(pathname, href);
            return (
              <Link
                key={href}
                href={href}
                onClick={onNavigate}
                className={cn(
                  'flex items-center gap-3 px-2 py-2 font-mono text-[0.78rem] uppercase tracking-[0.12em] transition-colors',
                  active
                    ? 'text-olive-deep border-l-2 border-olive-deep -ml-[2px] pl-[10px]'
                    : 'text-ink-soft hover:text-ink',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
