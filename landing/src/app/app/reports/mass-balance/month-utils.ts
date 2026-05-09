const MONTH_NAMES = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

export type MonthOption = { value: string; label: string };

export function buildMonthOptions(monthDates: string[]): MonthOption[] {
  const seen = new Set<string>();
  const opts: MonthOption[] = [];
  for (const d of monthDates) {
    const ym = d.slice(0, 7);
    if (seen.has(ym)) continue;
    seen.add(ym);
    const [y, m] = ym.split('-').map(Number);
    if (!y || !m) continue;
    opts.push({
      value: ym,
      label: `${MONTH_NAMES[m - 1]} ${String(y).slice(-2)}`,
    });
  }
  opts.sort((a, b) => b.value.localeCompare(a.value));
  return opts;
}
