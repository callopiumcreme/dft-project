'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Scale,
  Users,
  Award,
  FileText,
  Truck,
  Factory,
  UserCog,
  History,
  type LucideIcon,
} from 'lucide-react';

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  group?: string;
  tooltip?: string;
};

const NAV: NavItem[] = [
  { href: '/app', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/app/inputs', label: 'Daily inputs', icon: Truck, group: 'Operations' },
  { href: '/app/production', label: 'Daily production', icon: Factory, group: 'Operations' },
  { href: '/app/reports/mass-balance', label: 'Mass balance', icon: Scale, group: 'Reports' },
  { href: '/app/reports/by-supplier', label: 'By supplier', icon: Users, group: 'Reports' },
  { href: '/app/reports/closure-status', label: 'Daily closure', icon: Scale, group: 'Reports' },
  { href: '/app/suppliers', label: 'Suppliers', icon: Users, group: 'Master data' },
  { href: '/app/certificates', label: 'Certificates', icon: Award, group: 'Master data' },
  { href: '/app/contracts', label: 'Contracts', icon: FileText, group: 'Master data' },
  { href: '/app/users', label: 'Users', icon: UserCog, group: 'Admin' },
  {
    href: '/app/audit',
    label: 'Audit log',
    icon: History,
    group: 'Admin',
    tooltip: 'Compliance ISCC EU + traceability',
  },
];

function NavLink({
  item,
  active,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  onNavigate?: () => void;
}) {
  const { href, label, icon: Icon, tooltip } = item;
  const linkRef = useRef<HTMLAnchorElement | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  const show = () => {
    if (!tooltip || !linkRef.current) return;
    const r = linkRef.current.getBoundingClientRect();
    setPos({ top: r.top + r.height / 2, left: r.right + 12 });
  };
  const hide = () => setPos(null);

  return (
    <>
      <Link
        ref={linkRef}
        href={href}
        onClick={() => {
          hide();
          onNavigate?.();
        }}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        aria-label={tooltip ? `${label} — ${tooltip}` : undefined}
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
      {tooltip && pos && (
        <span
          role="tooltip"
          style={{ top: pos.top, left: pos.left, transform: 'translateY(-50%)' }}
          className="pointer-events-none fixed z-[100] whitespace-nowrap rounded-md border border-ink/15 bg-ink px-2.5 py-1.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-bg-soft shadow-lg"
        >
          {tooltip}
        </span>
      )}
    </>
  );
}

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
          {items.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              active={isActive(pathname, item.href)}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      ))}
    </nav>
  );
}
