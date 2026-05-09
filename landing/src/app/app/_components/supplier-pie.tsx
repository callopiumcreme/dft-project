'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

export type PieSlice = {
  name: string;
  value: number;
  pct: number;
};

const PALETTE = [
  '#6b7340', // olive-deep
  '#a89968', // olive
  '#7d8f4f',
  '#bba87a',
  '#5a6336',
  '#c9b888',
  '#857d6c',
];

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const pctFmt = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function SupplierPie({ data }: { data: PieSlice[] }) {
  if (data.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
        No suppliers in period
      </div>
    );
  }
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="40%"
            cy="50%"
            innerRadius={50}
            outerRadius={100}
            paddingAngle={1}
            stroke="#fbf9f4"
            strokeWidth={1}
            isAnimationActive={false}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: '#fbf9f4',
              border: '1px solid #d8d4cc',
              borderRadius: 0,
              fontFamily: 'monospace',
              fontSize: 11,
            }}
            formatter={(value, _name, item) => {
              const slice = item?.payload as PieSlice | undefined;
              return [`${numFmt.format(Number(value))} kg · ${pctFmt.format(slice?.pct ?? 0)} %`, slice?.name ?? ''];
            }}
          />
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            wrapperStyle={{
              fontFamily: 'monospace',
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
            }}
            formatter={(val) => <span className="text-ink-soft">{val}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
