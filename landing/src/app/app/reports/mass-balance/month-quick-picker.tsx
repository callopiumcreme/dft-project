'use client';

import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import type { MonthOption } from './month-utils';

function monthRange(yyyymm: string): { from: string; to: string } {
  const [y, m] = yyyymm.split('-').map(Number);
  const lastDay = new Date(y, m, 0).getDate();
  return {
    from: `${yyyymm}-01`,
    to: `${yyyymm}-${String(lastDay).padStart(2, '0')}`,
  };
}

function selectedYmFromRange(from?: string, to?: string): string {
  if (!from || !to) return '';
  if (from.length < 10 || to.length < 10) return '';
  if (from.slice(0, 7) !== to.slice(0, 7)) return '';
  if (!from.endsWith('-01')) return '';
  return from.slice(0, 7);
}

type Props = {
  options: MonthOption[];
  view: 'daily' | 'monthly';
  from?: string;
  to?: string;
};

export function MonthQuickPicker({ options, view, from, to }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const selected = selectedYmFromRange(from, to);

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const ym = e.target.value;
    if (!ym) {
      startTransition(() => router.push(`/app/reports/mass-balance?view=${view}`));
      return;
    }
    const { from: f, to: t } = monthRange(ym);
    startTransition(() =>
      router.push(`/app/reports/mass-balance?view=${view}&from=${f}&to=${t}`),
    );
  }

  return (
    <label className="flex flex-col gap-1">
      <span className="text-ink-mute">Quick</span>
      <select
        value={selected}
        onChange={handleChange}
        disabled={pending || options.length === 0}
        className="border border-rule bg-bg-soft px-2 py-1 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink disabled:opacity-60"
      >
        <option value="">— Month —</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
