import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deleteSupplierAction, restoreSupplierAction } from '@/lib/supplier-actions';
import { ErsvLink } from '@/components/ersv';
import { CertificatePdfLink } from '@/components/certificates';

type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];
type Certificate = components['schemas']['CertificateRead'];
type DailyInput = components['schemas']['DailyInputRead'];
type CertStatus = Certificate['status'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Supplier — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: { created?: string; updated?: string; restored?: string; error?: string };
}

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

const CERT_STATUS_LABEL: Record<CertStatus, string> = {
  active: 'Active',
  expired: 'Expired',
  revoked: 'Revoked',
  placeholder: 'Placeholder',
};

const CERT_STATUS_PILL: Record<CertStatus, string> = {
  active: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
  expired: 'border-ink-mute bg-bg text-ink-mute',
  revoked: 'border-accent bg-accent/5 text-accent',
  placeholder: 'border-ink-mute bg-bg text-ink-mute',
};

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-GB');
}

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return numFmt.format(n);
}

function totalKg(r: DailyInput): number {
  const car = Number(r.car_kg) || 0;
  const truck = Number(r.truck_kg) || 0;
  const special = Number(r.special_kg) || 0;
  return car + truck + special;
}

export default async function SupplierDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let supplier: Supplier | null = null;
  let me: UserRead | null = null;
  let certs: Certificate[] = [];
  let inputs: DailyInput[] = [];
  let inputCount = 0;
  let fetchError: string | null = null;

  try {
    [supplier, me, certs, inputs] = await Promise.all([
      apiGet<Supplier>(`/suppliers/${id}`, { query: { include_deleted: true } }),
      apiGet<UserRead>('/auth/me'),
      apiGet<Certificate[]>('/certificates', { query: { include_deleted: true } }),
      apiGet<DailyInput[]>('/daily-inputs', { query: { supplier_id: id, limit: 20 } }),
    ]);
    try {
      const cnt = await apiGet<{ count: number }>('/daily-inputs/count', {
        query: { supplier_id: id },
      });
      inputCount = cnt.count;
    } catch {
      // count is decorative — swallow and fall back to list length
      inputCount = inputs.length;
    }
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!supplier) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            <Link href="/app/suppliers" className="hover:text-ink">
              Suppliers
            </Link>{' '}
            / #{id}
          </p>
          <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Not found</h1>
        </header>
        {fetchError && (
          <div className="mt-6 border border-accent bg-accent/5 p-4 font-mono text-[0.75rem] text-accent">
            {fetchError}
          </div>
        )}
      </div>
    );
  }

  const isAdmin = me?.role === 'admin';
  const isDeleted = !!supplier.deleted_at;
  const supplierCerts = certs.filter((c) => c.supplier_ids.includes(id));

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/suppliers" className="hover:text-ink">
            Suppliers
          </Link>{' '}
          / {supplier.code}
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">
            {supplier.name}
            {isDeleted && (
              <span className="ml-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent">
                · deleted
              </span>
            )}
          </h1>
          {isAdmin && !isDeleted && (
            <div className="flex items-center gap-2">
              <Link
                href={`/app/suppliers/${supplier.id}/edit`}
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Edit
              </Link>
              <form action={deleteSupplierAction}>
                <input type="hidden" name="id" value={supplier.id} />
                <button
                  type="submit"
                  className="border border-accent px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent hover:bg-accent/10"
                >
                  Delete
                </button>
              </form>
            </div>
          )}
          {isAdmin && isDeleted && (
            <form action={restoreSupplierAction}>
              <input type="hidden" name="id" value={supplier.id} />
              <button
                type="submit"
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Restore
              </button>
            </form>
          )}
        </div>
        <p className="mt-3 font-mono text-[0.72rem] text-ink-soft">
          {supplier.code}
          {supplier.country ? ` · ${supplier.country}` : ''}
          {supplier.is_aggregate ? ' · aggregate' : ''}
          {supplier.active ? ' · active' : ' · inactive'}
          {' · '}
          {supplierCerts.length} cert{supplierCerts.length === 1 ? '' : 's'}
          {' · '}
          {inputCount} input{inputCount === 1 ? '' : 's'}
        </p>
      </header>

      {searchParams.created === '1' && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Supplier created
        </p>
      )}
      {searchParams.updated === '1' && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Supplier updated
        </p>
      )}
      {searchParams.restored === '1' && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Supplier restored
        </p>
      )}
      {searchParams.error && (
        <p
          role="alert"
          className="mt-6 border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent"
        >
          {searchParams.error}
        </p>
      )}

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Loading error: {fetchError}
        </div>
      )}

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DataBlock title="Identity">
          <Row label="Code">{supplier.code}</Row>
          <Row label="Name">{supplier.name}</Row>
          <Row label="Country">{supplier.country ?? '—'}</Row>
        </DataBlock>

        <DataBlock title="Status">
          <Row label="Active">{supplier.active ? 'yes' : 'no'}</Row>
          <Row label="Aggregate">{supplier.is_aggregate ? 'yes' : 'no'}</Row>
          <Row label="Deleted at">{fmtDateTime(supplier.deleted_at)}</Row>
        </DataBlock>

        {supplier.notes && (
          <DataBlock title="Notes" full>
            <p className="font-mono text-[0.78rem] text-ink whitespace-pre-wrap">{supplier.notes}</p>
          </DataBlock>
        )}

        <DataBlock title="Audit" full>
          <Row label="Created">{fmtDateTime(supplier.created_at)}</Row>
          <Row label="Updated">{fmtDateTime(supplier.updated_at)}</Row>
        </DataBlock>
      </section>

      <section className="mt-8">
        <h2 className="border-b border-rule pb-2 font-mono text-[0.72rem] uppercase tracking-[0.16em] text-ink-mute">
          Certificates ({supplierCerts.length})
        </h2>
        {supplierCerts.length === 0 ? (
          <p className="mt-4 font-mono text-[0.75rem] text-ink-mute">
            No certificates linked to this supplier.
          </p>
        ) : (
          <div className="mt-4 border border-rule bg-bg-soft overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[0.72rem]">
              <thead className="border-b border-rule bg-bg">
                <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                  <Th>Cert number</Th>
                  <Th>Scheme</Th>
                  <Th>Status</Th>
                  <Th>Issued</Th>
                  <Th>Expires</Th>
                  <Th>PDF</Th>
                  <Th className="text-right">
                    <span className="sr-only">Open</span>
                  </Th>
                </tr>
              </thead>
              <tbody>
                {supplierCerts.map((c) => {
                  const status = (c.status ?? 'active') as CertStatus;
                  const deleted = !!c.deleted_at;
                  return (
                    <tr
                      key={c.id}
                      className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                    >
                      <Td className="text-ink">
                        <Link
                          href={`/app/certificates/${c.id}`}
                          className="hover:text-olive-deep"
                        >
                          {c.cert_number}
                        </Link>
                      </Td>
                      <Td className="text-ink-soft">{c.scheme ?? '—'}</Td>
                      <Td>
                        <span
                          className={`inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${CERT_STATUS_PILL[status]}`}
                        >
                          {CERT_STATUS_LABEL[status]}
                        </span>
                        {deleted && (
                          <span className="ml-2 inline-block border border-accent bg-accent/5 px-2 py-0.5 text-[0.65rem] uppercase text-accent">
                            deleted
                          </span>
                        )}
                      </Td>
                      <Td className="text-ink-soft">{fmtDate(c.issued_at)}</Td>
                      <Td className="text-ink-soft">{fmtDate(c.expires_at)}</Td>
                      <Td>
                        {c.pdf_ref ? (
                          <CertificatePdfLink
                            certId={c.id}
                            header={{
                              certNumber: c.cert_number,
                              scheme: c.scheme ?? '—',
                              status: CERT_STATUS_LABEL[status],
                              issuedAt: c.issued_at ?? null,
                              expiresAt: c.expires_at ?? null,
                              isPlaceholder: !!c.is_placeholder,
                            }}
                            className="!border !border-olive-deep !bg-olive-deep !text-bg !no-underline hover:!bg-olive !decoration-transparent inline-block px-2 py-0.5 text-[0.65rem] uppercase tracking-[0.1em]"
                          >
                            PDF
                          </CertificatePdfLink>
                        ) : (
                          <span className="text-ink-mute">—</span>
                        )}
                      </Td>
                      <Td className="text-right">
                        <Link
                          href={`/app/certificates/${c.id}`}
                          className="text-ink-soft hover:text-ink"
                          aria-label={`Open certificate ${c.cert_number}`}
                        >
                          →
                        </Link>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="mt-8">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-rule pb-2">
          <h2 className="font-mono text-[0.72rem] uppercase tracking-[0.16em] text-ink-mute">
            Recent inbound eRSVs ({inputs.length}
            {inputCount > inputs.length ? ` of ${inputCount}` : ''})
          </h2>
          <Link
            href={`/app/inputs?supplier_id=${id}`}
            className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-soft hover:text-ink"
          >
            All inputs →
          </Link>
        </div>
        {inputs.length === 0 ? (
          <p className="mt-4 font-mono text-[0.75rem] text-ink-mute">
            No daily inputs recorded for this supplier.
          </p>
        ) : (
          <div className="mt-4 border border-rule bg-bg-soft overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[0.72rem]">
              <thead className="border-b border-rule bg-bg">
                <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                  <Th>Date</Th>
                  <Th>eRSV no.</Th>
                  <ThNum>Car kg</ThNum>
                  <ThNum>Truck kg</ThNum>
                  <ThNum>Special kg</ThNum>
                  <ThNum>Total kg</ThNum>
                  <Th className="text-right">
                    <span className="sr-only">Open</span>
                  </Th>
                </tr>
              </thead>
              <tbody>
                {inputs.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                  >
                    <Td className="text-ink-soft">{fmtDate(r.entry_date)}</Td>
                    <Td className="text-ink">
                      {r.ersv_number ? (
                        <ErsvLink ersvNumber={r.ersv_number} dailyInputId={r.id} />
                      ) : (
                        <span className="text-ink-mute">—</span>
                      )}
                    </Td>
                    <TdNum>{fmtKg(r.car_kg)}</TdNum>
                    <TdNum>{fmtKg(r.truck_kg)}</TdNum>
                    <TdNum>{fmtKg(r.special_kg)}</TdNum>
                    <TdNum className="text-ink">{numFmt.format(totalKg(r))}</TdNum>
                    <Td className="text-right">
                      <Link
                        href={`/app/inputs/${r.id}`}
                        className="text-ink-soft hover:text-ink"
                        aria-label={`Open daily input ${r.id}`}
                      >
                        →
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function DataBlock({
  title,
  children,
  full,
}: {
  title: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <section className={`border border-rule bg-bg-soft p-5 ${full ? 'sm:col-span-2' : ''}`}>
      <h2 className="mb-3 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
        {title}
      </h2>
      <dl className="space-y-1.5">{children}</dl>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-rule/40 pb-1.5 last:border-b-0 last:pb-0">
      <dt className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
        {label}
      </dt>
      <dd className="font-mono text-[0.78rem] text-ink-soft text-right">{children}</dd>
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
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <td className={`px-3 py-2 ${className}`}>{children}</td>;
}
function TdNum({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <td className={`px-3 py-2 text-right tabular-nums ${className}`}>{children}</td>;
}
