import {
  Ship,
  Warehouse,
  Truck,
  Anchor,
  PackageOpen,
  MapPin,
} from 'lucide-react';
import type { ShipmentLeg, LegType } from '@/types/logistics';

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${numFmt.format(n)} kg`;
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

const LEG_ICON: Record<LegType, React.ElementType> = {
  plant_to_port: Truck,
  port_loading: Anchor,
  bl_ocean: Ship,
  utb_transload: Warehouse,
  nl_to_uk_export: PackageOpen,
  delivery_uk: MapPin,
};

const LEG_LABEL: Record<LegType, string> = {
  plant_to_port: 'Plant → port',
  port_loading: 'Port loading',
  bl_ocean: 'Ocean BL',
  utb_transload: 'UTB transload',
  nl_to_uk_export: 'NL → UK export',
  delivery_uk: 'Delivery UK',
};

function isKnownLegType(v: string): v is LegType {
  return v in LEG_LABEL;
}

interface ChainTimelineProps {
  legs: ShipmentLeg[];
}

export function ChainTimeline({ legs }: ChainTimelineProps) {
  const sorted = [...legs].sort((a, b) => a.seq - b.seq);

  return (
    <ol className="relative flex flex-col gap-0">
      {sorted.map((leg, idx) => {
        const legType = isKnownLegType(leg.leg_type) ? leg.leg_type : 'bl_ocean';
        const Icon = LEG_ICON[legType];
        const label = LEG_LABEL[legType];
        const isLast = idx === sorted.length - 1;
        const isTransload = leg.leg_type === 'utb_transload';

        return (
          <li key={leg.id} className="relative flex gap-4">
            {/* Timeline spine */}
            <div className="flex flex-col items-center">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-rule bg-bg-soft">
                <Icon className="h-4 w-4 text-ink-soft" aria-hidden />
              </div>
              {!isLast && (
                <div className="w-px flex-1 bg-rule" style={{ minHeight: '2rem' }} />
              )}
            </div>

            {/* Card */}
            <div className={`mb-4 flex-1 border border-rule bg-bg-soft p-4 ${isLast ? '' : ''}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
                    Step {leg.seq} · {label}
                  </p>
                  <p className="mt-0.5 font-mono text-[0.78rem] text-ink">
                    {leg.origin_node}
                    <span className="mx-2 text-ink-mute">→</span>
                    {leg.destination_node}
                  </p>
                </div>
                <MassBalanceBadge leg={leg} />
              </div>

              <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-[0.7rem]">
                {leg.document_ref && (
                  <>
                    <span className="text-ink-mute uppercase tracking-[0.12em]">
                      {leg.document_type ?? 'Document'}
                    </span>
                    <span className="text-ink">{leg.document_ref}</span>
                  </>
                )}
                {leg.document_date && (
                  <>
                    <span className="text-ink-mute uppercase tracking-[0.12em]">Date</span>
                    <span className="text-ink">{fmtDate(leg.document_date)}</span>
                  </>
                )}
                {leg.carrier && (
                  <>
                    <span className="text-ink-mute uppercase tracking-[0.12em]">Carrier</span>
                    <span className="text-ink">{leg.carrier}</span>
                  </>
                )}
                <>
                  <span className="text-ink-mute uppercase tracking-[0.12em]">kg in</span>
                  <span className="text-ink tabular-nums">{fmtKg(leg.kg_in)}</span>
                </>
                <>
                  <span className="text-ink-mute uppercase tracking-[0.12em]">kg out</span>
                  <span className="text-ink tabular-nums">{fmtKg(leg.kg_out)}</span>
                </>
                {isTransload && leg.kg_stock_residual && (
                  <>
                    <span className="text-ink-mute uppercase tracking-[0.12em]">Stock residual</span>
                    <span className="text-ink tabular-nums">{fmtKg(leg.kg_stock_residual)}</span>
                  </>
                )}
              </div>

              {leg.notes && (
                <p className="mt-3 border-t border-rule pt-3 font-mono text-[0.7rem] text-ink-soft">
                  {leg.notes}
                </p>
              )}

              {leg.units.length > 0 && (
                <details className="mt-3 border-t border-rule pt-3">
                  <summary className="cursor-pointer font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute hover:text-ink">
                    {leg.units.length} units — expand
                  </summary>
                  <div className="mt-2 overflow-x-auto">
                    <table className="w-full border-collapse font-mono text-[0.68rem]">
                      <thead>
                        <tr className="border-b border-rule text-left uppercase tracking-[0.1em] text-ink-mute">
                          <th className="px-2 py-1 font-normal">Container / ref</th>
                          <th className="px-2 py-1 font-normal">Flexitank</th>
                          <th className="px-2 py-1 text-right font-normal">Gross kg</th>
                          <th className="px-2 py-1 text-right font-normal">Tare kg</th>
                          <th className="px-2 py-1 text-right font-normal">Net kg</th>
                        </tr>
                      </thead>
                      <tbody>
                        {leg.units.map((u) => (
                          <tr
                            key={u.id}
                            className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                          >
                            <td className="px-2 py-1 text-ink">{u.container_ref ?? '—'}</td>
                            <td className="px-2 py-1 text-ink-soft">{u.flexitank_ref ?? '—'}</td>
                            <td className="px-2 py-1 text-right tabular-nums text-ink-soft">
                              {fmtKg(u.kg_gross)}
                            </td>
                            <td className="px-2 py-1 text-right tabular-nums text-ink-soft">
                              {fmtKg(u.kg_tare)}
                            </td>
                            <td className="px-2 py-1 text-right tabular-nums text-ink">
                              {fmtKg(u.kg_net)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function MassBalanceBadge({ leg }: { leg: ShipmentLeg }) {
  const kgIn = Number(leg.kg_in) || 0;
  const kgOut = Number(leg.kg_out) || 0;
  const isTransload = leg.leg_type === 'utb_transload';

  if (isTransload && leg.kg_stock_residual) {
    return (
      <span className="inline-block border border-rule bg-bg px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.1em] text-ink-soft">
        in / out / residual
      </span>
    );
  }

  const balanced = Math.abs(kgIn - kgOut) < 1;
  return (
    <span
      className={`inline-block border px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.1em] ${
        balanced
          ? 'border-olive-deep bg-olive-deep/10 text-olive-deep'
          : 'border-accent bg-accent/5 text-accent'
      }`}
    >
      {balanced ? 'balanced' : 'mismatch'}
    </span>
  );
}
