import Link from 'next/link';

export function SiteFooter() {
  return (
    <footer className="border-t border-rule bg-bg">
      <div className="mx-auto flex max-w-editorial flex-col items-start gap-2 px-6 py-5 font-mono text-[0.68rem] uppercase tracking-[0.14em] text-ink-mute sm:flex-row sm:items-center sm:justify-between">
        <p>
          OisteBio GmbH · Baar (CH) · MWSt CHE-234.625.162
        </p>
        <nav className="flex items-center gap-5">
          <Link
            href="/terms"
            className="hover:text-ink"
          >
            Terms of Use
          </Link>
          <a
            href="mailto:export@oistebio.ch"
            className="hover:text-ink"
          >
            Contact
          </a>
        </nav>
      </div>
    </footer>
  );
}
