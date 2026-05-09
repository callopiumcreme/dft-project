'use client';

import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export type SparkPoint = {
  day: string;
  input: number;
  output: number;
};

function fmtKg(n: number) {
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 }).format(n);
}

function fmtDay(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit' });
}

export function Sparkline({ data }: { data: SparkPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
        No data available
      </div>
    );
  }
  return (
    <div className="h-40 w-full">
      <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <XAxis
            dataKey="day"
            tickFormatter={fmtDay}
            tick={{ fontSize: 10, fontFamily: 'monospace', fill: '#857d6c' }}
            axisLine={{ stroke: '#d8d4cc' }}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            tickFormatter={(v) => fmtKg(Number(v))}
            tick={{ fontSize: 10, fontFamily: 'monospace', fill: '#857d6c' }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <Tooltip
            contentStyle={{
              background: '#fbf9f4',
              border: '1px solid #d8d4cc',
              borderRadius: 0,
              fontFamily: 'monospace',
              fontSize: 11,
            }}
            labelFormatter={(label) => fmtDay(String(label))}
            formatter={(value, name) => [`${fmtKg(Number(value))} kg`, name === 'input' ? 'Input' : 'Output']}
          />
          <Line
            type="monotone"
            dataKey="input"
            stroke="#6b7340"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="output"
            stroke="#a89968"
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
