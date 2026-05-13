'use client';

import { useRef, useState } from 'react';

export function KpiTileTooltip({
  label,
  value,
  tooltip,
}: {
  label: string;
  value: string;
  tooltip: string;
}) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  const show = () => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    setPos({ top: r.top - 8, left: r.left + r.width / 2 });
  };
  const hide = () => setPos(null);

  return (
    <>
      <div
        ref={ref}
        tabIndex={0}
        role="group"
        aria-label={`${label} — ${tooltip}`}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        className="border border-rule bg-bg-soft p-4 outline-none focus:border-ink"
      >
        <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          {label}
        </p>
        <p className="mt-2 font-display text-2xl tracking-editorial text-ink">{value}</p>
      </div>
      {pos && (
        <span
          role="tooltip"
          style={{ top: pos.top, left: pos.left, transform: 'translate(-50%, -100%)' }}
          className="pointer-events-none fixed z-[100] whitespace-nowrap rounded-md border border-ink/15 bg-ink px-2.5 py-1.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-bg-soft shadow-lg"
        >
          {tooltip}
        </span>
      )}
    </>
  );
}
