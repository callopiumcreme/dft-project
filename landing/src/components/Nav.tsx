'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

const NAV = [
  { label: 'Problem', href: '#problem' },
  { label: 'Solution', href: '#solution' },
  { label: 'Compliance', href: '#compliance' },
  { label: 'Case study', href: '#case-study' },
  { label: 'FAQ', href: '#faq' },
];

export function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={cn(
        'fixed top-0 inset-x-0 z-50 transition-all duration-500',
        scrolled
          ? 'bg-bg/85 backdrop-blur-md border-b border-rule'
          : 'bg-transparent border-b border-transparent'
      )}
    >
      <div className="container-edit flex items-center justify-between h-16">
        <Link
          href="/"
          aria-label="OisteBio — home"
          className="flex items-center gap-3 group"
        >
          <Image
            src="/logo.png"
            alt="OisteBio"
            width={160}
            height={60}
            priority
            className="h-9 w-auto"
          />
          <span className="hidden sm:inline eyebrow ml-1 text-ink-mute">
            Pyrolysis traceability
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-7" aria-label="Primary">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="font-mono text-[0.72rem] uppercase tracking-[0.16em] text-ink-soft hover:text-olive transition-colors"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <a
            href="https://app.dft-project.com"
            className="hidden sm:inline font-mono text-[0.72rem] uppercase tracking-[0.16em] text-ink-soft hover:text-ink transition-colors"
          >
            Sign in
          </a>
          <a
            href="#contact"
            className="inline-flex items-center font-mono text-[0.72rem] uppercase tracking-[0.16em] bg-ink text-bg h-9 px-4 hover:bg-olive-deep transition-colors"
          >
            Request demo
          </a>
        </div>
      </div>
    </header>
  );
}
