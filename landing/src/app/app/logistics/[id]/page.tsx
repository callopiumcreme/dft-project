import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import { ChainTimeline } from '@/components/logistics/ChainTimeline';
import { OutboundErsvLink } from '@/components/ersv-outbound';
import { InlandErsvLink } from '@/components/ersv-inland';
import { UmamiViewEvent } from '@/components/analytics/umami-view-event';
import type { ConsignmentDetail, ConsignmentStatus } from '@/types/logistics';

interface InlandShipmentRow {
  shipment_id: number;
  consignment_id: number;
  consignment_code: string;
  bl_ref: string;
  seq_in_bl: number;
  container_id: string;
  seal_ref: string | null;
  load_date: string;
  gross_kg: number;
  tare_kg: number;
  net_kg: number;
  ersv_inland_no: string | null;
}

export const dynamic = 'force-dynamic';

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

const STATUS_LABEL: Record<ConsignmentStatus, string> = {
  draft: 'Draft',
  loaded: 'Loaded',
  in_transit: 'In transit',
  at_utb: 'At UTB',
  delivered_uk: 'Delivered UK',
  closed: 'Closed',
};

const STATUS_PILL: Record<ConsignmentStatus, string> = {
  draft: 'border-rule bg-bg text-ink-mute',
  loaded: 'border-rule bg-bg text-ink-soft',
  in_transit: 'border-ink-soft bg-bg text-ink-soft',
  at_utb: 'border-ink bg-ink/5 text-ink',
  delivered_uk: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
  closed: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
};

const ALL_STATUSES = Object.keys(STATUS_LABEL) as ConsignmentStatus[];

function isStatus(v: string): v is ConsignmentStatus {
  return (ALL_STATUSES as string[]).includes(v);
}

const ID_RE = /^\d{1,9}$/;

interface PageProps {
  params: { id: string };
}

export default async function ConsignmentDetailPage({ params }: PageProps) {
  if (!ID_RE.test(params.id)) notFound();

  let consignment: ConsignmentDetail;
  let inlandShipments: InlandShipmentRow[] = [];
  try {
    consignment = await apiGet<ConsignmentDetail>(`/consignments/${params.id}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    const errMsg =
      e instanceof ApiError ? `${e.status} · ${e.detail}` : 'Unknown error';
    return (
      <div className="mx-auto max-w-editorial">
        <div className="mt-10 border border-rule bg-bg-soft p-6 font-mono text-[0.75rem] text-accent">
          Failed to load consignment {params.id}: {errMsg}
        </div>
        <div className="mt-4">
          <Link
            href="/app/logistics"
            className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-soft hover:text-ink"
          >
            ← Back to Logistics
          </Link>
        </div>
      </div>
    );
  }

  try {
    inlandShipments = await apiGet<InlandShipmentRow[]>(
      `/ersv/inland?consignment_id=${consignment.id}&page_size=200`,
    );
  } catch {
    inlandShipments = [];
  }

  const status = isStatus(consignment.status) ? consignment.status : 'draft';

  // Aggregate unit count across all legs
  const totalUnits = consignment.legs.reduce((s, l) => s + l.units.length, 0);

  // Per-PoS eRSV is per-row now (since 0022). Count allocated for header chip.
  const ersvAllocated = consignment.pos.filter((p) => p.ersv_outbound_no).length;

  return (
    <div className="mx-auto max-w-editorial">
      <UmamiViewEvent
        name="view_consignment"
        data={{
          id: consignment.id,
          code: consignment.code,
          status: consignment.status,
        }}
      />
      {/* Breadcrumb nav */}
      <div className="mb-4">
        <Link
          href="/app/logistics"
          className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-soft hover:text-ink"
        >
          ← Logistics
        </Link>
      </div>

      {/* Header */}
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Consignment
        </p>
        <div className="mt-1 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl tracking-editorial text-ink">
              {consignment.code}
            </h1>
            <p className="mt-2 font-mono text-[0.78rem] text-ink-soft">
              {consignment.off_taker?.name ?? 'Unknown off-taker'} ·{' '}
              {consignment.product_grade}
            </p>
          </div>

          {/* eRSV is per-PoS since 0022 — render/download buttons live on each PoS row below */}
        </div>

        {/* Meta */}
        <div className="mt-4 flex flex-wrap gap-3">
          <span
            className={`inline-block border px-2 py-0.5 font-mono text-[0.65rem] uppercase ${STATUS_PILL[status]}`}
          >
            {STATUS_LABEL[status]}
          </span>
          {consignment.pos.length > 0 && (
            <span className="inline-block border border-rule bg-bg px-2 py-0.5 font-mono text-[0.65rem] uppercase text-ink-soft">
              eRSV {ersvAllocated}/{consignment.pos.length} allocated
            </span>
          )}
          {consignment.port_rsv_no && (
            <span className="inline-block border border-rule bg-bg px-2 py-0.5 font-mono text-[0.65rem] uppercase text-ink-soft">
              Port RSV {consignment.port_rsv_no}
            </span>
          )}
        </div>

        <dl className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2 font-mono text-[0.72rem]">
          <div>
            <dt className="text-ink-mute uppercase tracking-[0.12em]">Total kg</dt>
            <dd className="mt-0.5 text-ink tabular-nums">{fmtKg(consignment.total_kg)}</dd>
          </div>
          <div>
            <dt className="text-ink-mute uppercase tracking-[0.12em]">Prod from</dt>
            <dd className="mt-0.5 text-ink">{fmtDate(consignment.prod_date_from)}</dd>
          </div>
          <div>
            <dt className="text-ink-mute uppercase tracking-[0.12em]">Prod to</dt>
            <dd className="mt-0.5 text-ink">{fmtDate(consignment.prod_date_to)}</dd>
          </div>
          <div>
            <dt className="text-ink-mute uppercase tracking-[0.12em]">Legs / units</dt>
            <dd className="mt-0.5 text-ink">
              {consignment.legs.length} / {totalUnits}
            </dd>
          </div>
        </dl>
      </header>

      {/* Chain of custody timeline */}
      <section className="mt-10">
        <h2 className="mb-6 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-ink-mute">
          Chain of custody
        </h2>
        {consignment.legs.length === 0 ? (
          <p className="font-mono text-[0.75rem] text-ink-mute">No shipment legs recorded.</p>
        ) : (
          <ChainTimeline legs={consignment.legs} />
        )}
      </section>

      {/* Linked PoS */}
      {consignment.pos.length > 0 && (
        <section className="mt-10 border-t border-rule pt-8">
          <h2 className="mb-4 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-ink-mute">
            Linked PoS ({consignment.pos.length})
          </h2>
          <div className="border border-rule bg-bg-soft overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[0.72rem]">
              <thead className="border-b border-rule bg-bg">
                <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                  <Th>PoS number</Th>
                  <ThNum>kg net</ThNum>
                  <Th>PDF</Th>
                  <Th>eRSV outbound</Th>
                  <Th className="text-right">
                    <span className="sr-only">Render</span>
                  </Th>
                </tr>
              </thead>
              <tbody>
                {consignment.pos.map((p) => (
                  <tr
                    key={`${p.consignment_id}-${p.pos_number}`}
                    className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                  >
                    <Td className="text-ink">{p.pos_number}</Td>
                    <TdNum>{fmtKg(p.kg_net)}</TdNum>
                    <Td>
                      {p.pdf_ref ? (
                        <span
                          className="cursor-help font-mono text-[0.65rem] uppercase tracking-[0.1em] text-ink-mute underline decoration-dotted underline-offset-2"
                          title={`Stored on Google Drive: ${p.pdf_ref}`}
                        >
                          gdrive
                        </span>
                      ) : (
                        <span className="text-ink-mute">—</span>
                      )}
                    </Td>
                    <Td className="text-ink-soft">
                      {p.ersv_outbound_no ?? (
                        <span className="text-ink-mute">—</span>
                      )}
                    </Td>
                    <Td className="text-right">
                      <OutboundErsvLink
                        consignmentId={consignment.id}
                        posNumber={p.pos_number}
                        header={{
                          offTakerCode: consignment.off_taker?.code ?? null,
                          posNumber: p.pos_number,
                          kgNet: p.kg_net,
                          ersvOutboundNo: p.ersv_outbound_no,
                          prodDateFrom: consignment.prod_date_from,
                          prodDateTo: consignment.prod_date_to,
                        }}
                        className="!border !border-olive-deep !bg-olive-deep !text-bg !no-underline hover:!bg-olive !decoration-transparent inline-block px-2 py-0.5 text-[0.65rem] uppercase tracking-[0.1em]"
                      >
                        Render
                      </OutboundErsvLink>
                    </Td>
                  </tr>
                ))}
                <tr className="border-t border-rule bg-bg font-semibold text-ink">
                  <Td>TOT</Td>
                  <TdNum>
                    {fmtKg(
                      String(
                        consignment.pos.reduce((s, p) => s + (Number(p.kg_net) || 0), 0),
                      ),
                    )}
                  </TdNum>
                  <Td>{null}</Td>
                  <Td>{null}</Td>
                  <Td>{null}</Td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-2 font-mono text-[0.68rem] text-ink-mute">
            PoS = Outgoing Material Declaration ISCC (OISCRO-XXXX-25 series).
            Each PoS carries its own outbound eRSV (CO/{'{yy}'}/{'{seq}'}) + GHG values per cliente direction 2026-05-23.
            PDFs stored on Google Drive — download via direct gdrive path.
          </p>
        </section>
      )}

      {/* Inland CO (Girardot → Cartagena) */}
      {inlandShipments.length > 0 && (
        <section className="mt-10 border-t border-rule pt-8">
          <h2 className="mb-4 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-ink-mute">
            Inland CO (Girardot → Cartagena) — {inlandShipments.length} contenedores
          </h2>
          <div className="border border-rule bg-bg-soft overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[0.72rem]">
              <thead className="border-b border-rule bg-bg">
                <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                  <Th>BL / Seq</Th>
                  <Th>Container</Th>
                  <Th>Seal</Th>
                  <Th>Load date</Th>
                  <ThNum>kg net</ThNum>
                  <Th>eRSV inland</Th>
                  <Th className="text-right">
                    <span className="sr-only">Render</span>
                  </Th>
                </tr>
              </thead>
              <tbody>
                {inlandShipments.map((s) => (
                  <tr
                    key={s.shipment_id}
                    className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                  >
                    <Td className="text-ink-soft">
                      {s.bl_ref}/{s.seq_in_bl}
                    </Td>
                    <Td className="text-ink">{s.container_id}</Td>
                    <Td className="text-ink-soft">
                      {s.seal_ref ?? <span className="text-ink-mute">—</span>}
                    </Td>
                    <Td className="text-ink-soft">{fmtDate(s.load_date)}</Td>
                    <TdNum>{fmtKg(String(s.net_kg))}</TdNum>
                    <Td className="text-ink-soft">
                      {s.ersv_inland_no ?? (
                        <span className="text-ink-mute">—</span>
                      )}
                    </Td>
                    <Td className="text-right">
                      <InlandErsvLink
                        shipmentId={s.shipment_id}
                        header={{
                          containerId: s.container_id,
                          sealRef: s.seal_ref,
                          loadDate: s.load_date,
                          netKg: String(s.net_kg),
                          ersvInlandNo: s.ersv_inland_no,
                        }}
                        className="!border !border-olive-deep !bg-olive-deep !text-bg !no-underline hover:!bg-olive !decoration-transparent inline-block px-2 py-0.5 text-[0.65rem] uppercase tracking-[0.1em]"
                      >
                        Render
                      </InlandErsvLink>
                    </Td>
                  </tr>
                ))}
                <tr className="border-t border-rule bg-bg font-semibold text-ink">
                  <Td>TOT</Td>
                  <Td>{null}</Td>
                  <Td>{null}</Td>
                  <Td>{null}</Td>
                  <TdNum>
                    {fmtKg(
                      String(
                        inlandShipments.reduce(
                          (acc, s) => acc + (Number(s.net_kg) || 0),
                          0,
                        ),
                      ),
                    )}
                  </TdNum>
                  <Td>{null}</Td>
                  <Td>{null}</Td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="mt-2 font-mono text-[0.68rem] text-ink-mute">
            eRSV inland (GIR/{'{yy}'}/{'{DD-MM}'}/{'{seq}'}) emitido por OisteBio GmbH —
            tránsito intra-entidad Girardot planta → Cartagena Contecar terminal portuaria.
            Numeración perezosa: se asigna en el primer render.
          </p>
        </section>
      )}

      {/* Production allocation */}
      {consignment.production_links.length > 0 && (
        <section className="mt-10 border-t border-rule pt-8">
          <h2 className="mb-4 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-ink-mute">
            Production allocation ({consignment.production_links.length} days)
          </h2>
          <div className="border border-rule bg-bg-soft overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[0.72rem]">
              <thead className="border-b border-rule bg-bg">
                <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                  <Th>Production date</Th>
                  <ThNum>kg allocated</ThNum>
                </tr>
              </thead>
              <tbody>
                {consignment.production_links.map((pl) => (
                  <tr
                    key={pl.prod_date}
                    className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                  >
                    <Td className="text-ink">{fmtDate(pl.prod_date)}</Td>
                    <TdNum>{fmtKg(pl.kg_allocated)}</TdNum>
                  </tr>
                ))}
                <tr className="border-t border-rule bg-bg font-semibold text-ink">
                  <Td>TOT</Td>
                  <TdNum>
                    {fmtKg(
                      String(
                        consignment.production_links.reduce(
                          (s, pl) => s + (Number(pl.kg_allocated) || 0),
                          0,
                        ),
                      ),
                    )}
                  </TdNum>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Notes */}
      {consignment.notes && (
        <section className="mt-10 border-t border-rule pt-8">
          <h2 className="mb-2 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-ink-mute">
            Notes
          </h2>
          <p className="font-mono text-[0.78rem] leading-relaxed text-ink-soft">
            {consignment.notes}
          </p>
        </section>
      )}
    </div>
  );
}

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-normal ${className}`}>{children}</th>;
}
function ThNum({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-right font-normal">{children}</th>;
}
function Td({
  className = '',
  children,
  title,
}: {
  className?: string;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <td className={`px-3 py-2 ${className}`} title={title}>
      {children}
    </td>
  );
}
function TdNum({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <td className={`px-3 py-2 text-right tabular-nums ${className}`}>{children}</td>;
}
