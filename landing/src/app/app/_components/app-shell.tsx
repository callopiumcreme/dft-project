'use client';

import { useState, type ReactNode } from 'react';
import Link from 'next/link';
import { Menu } from 'lucide-react';
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from '@/components/ui/sheet';
import { SidebarNav } from './sidebar-nav';
import { Breadcrumb } from './breadcrumb';
import { UserMenu } from './user-menu';

type Props = {
  children: ReactNode;
  user: { email: string; role: string; full_name?: string | null };
};

export function AppShell({ children, user }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-bg">
      <aside className="hidden md:flex md:fixed md:inset-y-0 md:left-0 md:w-60 md:flex-col md:border-r md:border-rule md:bg-bg">
        <Link
          href="/app"
          className="flex h-16 items-center border-b border-rule px-6 font-display text-2xl tracking-editorial text-ink hover:text-olive-deep transition-colors"
        >
          DFT
        </Link>
        <div className="flex-1 overflow-y-auto">
          <SidebarNav />
        </div>
        <div className="border-t border-rule px-6 py-4 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Mass balance · v0.2
        </div>
      </aside>

      <div className="md:pl-60">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-rule bg-bg/95 backdrop-blur px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger
                className="md:hidden -ml-1 grid h-9 w-9 place-items-center text-ink-soft hover:text-ink focus-visible:ring-2 focus-visible:ring-olive outline-none"
                aria-label="Apri menu"
              >
                <Menu className="h-5 w-5" />
              </SheetTrigger>
              <SheetContent side="left" className="w-72 p-0">
                <SheetTitle className="sr-only">Navigazione</SheetTitle>
                <Link
                  href="/app"
                  onClick={() => setOpen(false)}
                  className="flex h-16 items-center border-b border-rule px-6 font-display text-2xl tracking-editorial text-ink"
                >
                  DFT
                </Link>
                <SidebarNav onNavigate={() => setOpen(false)} />
              </SheetContent>
            </Sheet>
            <Breadcrumb />
          </div>
          <UserMenu email={user.email} role={user.role} fullName={user.full_name} />
        </header>
        <main className="px-4 sm:px-6 lg:px-10 py-8">{children}</main>
      </div>
    </div>
  );
}
