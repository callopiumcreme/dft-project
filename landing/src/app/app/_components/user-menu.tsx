'use client';

import { useTransition } from 'react';
import { ChevronDown, LogOut } from 'lucide-react';
import { logoutAction } from '@/lib/auth';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

type Props = {
  email: string;
  role: string;
  fullName?: string | null;
};

export function UserMenu({ email, role, fullName }: Props) {
  const [pending, startTransition] = useTransition();
  const display = fullName ?? email;
  const initials = display
    .split(/[\s.@]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join('');

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex items-center gap-2 px-2 py-1.5 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft outline-none transition-colors hover:text-ink focus-visible:ring-2 focus-visible:ring-olive disabled:opacity-60"
        disabled={pending}
      >
        <span
          className="grid h-7 w-7 place-items-center bg-olive text-bg font-mono text-[0.7rem] tracking-normal"
          aria-hidden
        >
          {initials || '·'}
        </span>
        <span className="hidden sm:inline">{display}</span>
        <ChevronDown className="h-3.5 w-3.5" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[14rem]">
        <DropdownMenuLabel>User</DropdownMenuLabel>
        <div className="px-2 pb-2">
          <p className="font-display text-sm tracking-editorial text-ink truncate">{display}</p>
          <p className="mt-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute truncate">
            {email}
          </p>
          <p className="mt-1 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-olive-deep">
            {role}
          </p>
        </div>
        <DropdownMenuSeparator />
        <form action={() => startTransition(() => logoutAction())}>
          <button
            type="submit"
            disabled={pending}
            className="flex w-full items-center gap-2 px-2 py-1.5 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft outline-none transition-colors hover:bg-bg-soft hover:text-accent focus:bg-bg-soft disabled:opacity-60"
          >
            <LogOut className="h-3.5 w-3.5" aria-hidden />
            {pending ? 'Signing out…' : 'Logout'}
          </button>
        </form>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
