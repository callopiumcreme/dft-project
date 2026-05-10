import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deleteInputAction } from '@/lib/inputs-actions';

type Input = components['schemas']['DailyInputRead'];
type Supplier = components['schemas']['SupplierRead'];
type Certificate = components['schemas']['CertificateRead'];
type Contract = components['schemas']['ContractRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Input detail — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: { updated?: string; error?: string };
}

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 3 }).format(n);
}

function fmtPct(v: string | null | undefined): string {
  if (!v) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${n.toFixed(2)}%`;
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-GB');
}

export default async function InputDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let input: Input | null = null;
  let suppliers: Supplier[] = [];
  let certificates: Certificate[] = [];
  let contracts: Contract[] = [];
  let fetchError: string | null = null;

  try {
    [input, suppliers, certificates, contracts] = await Promise.all([
      apiGet<Input>(`/daily-inputs/${id}`, { query: { include_deleted: true } }),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
      apiGet<Certificate[]>('/certificates', { query: { active_only: false } }),
      apiGet<Contract[]>('/contracts', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!input) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            <Link href="/app/inputs" className="hover:text-ink">
              Inputs
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

  const supplier = suppliers.find((s) => s.id === input!.supplier_id);
  const certificate = certificates.find((c) => c.id === input!.certificate_id);
  const contract = contracts.find((c) => c.id === input!.contract_id);

  const isDeleted = !!input.deleted_at;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/inputs" className="hover:text-ink">
            Inputs
          </Link>{' '}
          / #{input.id}
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">
            Input #{input.id}
            {isDeleted && (
              <span className="ml-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent">
                · deleted
              </span>
            )}
          </h1>
          {!isDeleted && (
            <div className="flex items-center gap-2">
              <Link
                href={`/app/inputs/${input.id}/edit`}
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Edit
              </Link>
              <form action={deleteInputAction}>
                <input type="hidden" name="id" value={input.id} />
                <button
                  type="submit"
                  className="border border-accent px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent hover:bg-accent/10"
                >
                  Delete
                </button>
              </form>
            </div>
          )}
        </div>
        <p className="mt-3 font-mono text-[0.72rem] text-ink-soft">
          {input.entry_date}
          {input.entry_time ? ` · ${input.entry_time}` : ''} ·{' '}
          {supplier ? `${supplier.code} · ${supplier.name}` : `supplier #${input.supplier_id}`}
        </p>
      </header>

      {searchParams.updated === '1' && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Input updated
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

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DataBlock title="References">
          <Row label="Certificate">
            {certificate ? `${certificate.cert_number} · ${certificate.scheme ?? '—'}` : '—'}
          </Row>
          <Row label="Contract">{contract ? contract.code : '—'}</Row>
          <Row label="eRSV">{input.ersv_number ?? '—'}</Row>
        </DataBlock>

        <DataBlock title="Weights (kg)">
          <Row label="Car">{fmtKg(input.car_kg)}</Row>
          <Row label="Truck">{fmtKg(input.truck_kg)}</Row>
          <Row label="Special">{fmtKg(input.special_kg)}</Row>
          <Row label="Total" emphasize>
            {fmtKg(input.total_input_kg)}
          </Row>
        </DataBlock>

        <DataBlock title="Veg %">
          <Row label="Theoretical">{fmtPct(input.theor_veg_pct)}</Row>
          <Row label="Manufactured">{fmtPct(input.manuf_veg_pct)}</Row>
        </DataBlock>

        <DataBlock title="C14">
          <Row label="Analysis">{input.c14_analysis ?? '—'}</Row>
          <Row label="Value">{input.c14_value ?? '—'}</Row>
        </DataBlock>

        {input.notes && (
          <DataBlock title="Notes" full>
            <p className="font-mono text-[0.78rem] text-ink whitespace-pre-wrap">{input.notes}</p>
          </DataBlock>
        )}

        <DataBlock title="Audit" full>
          <Row label="Created">
            {fmtDateTime(input.created_at)}
            {input.created_by ? ` · user #${input.created_by}` : ''}
          </Row>
          <Row label="Updated">
            {fmtDateTime(input.updated_at)}
            {input.updated_by ? ` · user #${input.updated_by}` : ''}
          </Row>
          {input.source_file && (
            <Row label="Source">
              {input.source_file}
              {input.source_row !== null && input.source_row !== undefined
                ? ` · row ${input.source_row}`
                : ''}
            </Row>
          )}
        </DataBlock>
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

function Row({
  label,
  children,
  emphasize,
}: {
  label: string;
  children: React.ReactNode;
  emphasize?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-rule/40 pb-1.5 last:border-b-0 last:pb-0">
      <dt className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">{label}</dt>
      <dd
        className={`font-mono text-[0.78rem] ${emphasize ? 'text-ink font-medium' : 'text-ink-soft'} text-right`}
      >
        {children}
      </dd>
    </div>
  );
}
