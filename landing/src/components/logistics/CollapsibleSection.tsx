/**
 * Native <details>/<summary> wrapper styled to match the logistics-page
 * editorial typography. Server-component friendly (no client JS).
 *
 * Use as a drop-in container for the long sub-blocks on
 * /app/logistics/[id] so the page does not require km of scroll —
 * each block opens on click.
 */
import { ChevronRight } from 'lucide-react';

interface Props {
  title: string;
  /** Optional right-aligned chip (e.g. row count) shown in the header. */
  badge?: React.ReactNode;
  /** Heading level — h2 for top-level sections, h3 for sub-blocks. */
  level?: 'h2' | 'h3';
  /** Whether to render expanded on first paint. */
  defaultOpen?: boolean;
  /** Optional outer wrapper class. */
  className?: string;
  children: React.ReactNode;
}

export function CollapsibleSection({
  title,
  badge,
  level = 'h3',
  defaultOpen = false,
  className = '',
  children,
}: Props) {
  const titleClass =
    level === 'h2'
      ? 'font-mono text-[0.7rem] uppercase tracking-[0.18em] text-ink-mute'
      : 'font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft';

  return (
    <details
      open={defaultOpen}
      className={`group border-t border-rule first:border-t-0 ${className}`}
    >
      <summary
        className="flex cursor-pointer list-none items-center justify-between gap-3 py-3 hover:bg-bg-soft/60 [&::-webkit-details-marker]:hidden"
      >
        <span className="flex items-center gap-2">
          <ChevronRight
            className="h-3.5 w-3.5 text-ink-mute transition-transform group-open:rotate-90"
            aria-hidden
          />
          <span className={titleClass}>{title}</span>
        </span>
        {badge && (
          <span className="font-mono text-[0.65rem] uppercase tracking-[0.1em] text-ink-mute">
            {badge}
          </span>
        )}
      </summary>
      <div className="pb-6 pt-1">{children}</div>
    </details>
  );
}
