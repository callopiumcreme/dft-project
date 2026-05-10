import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deleteContractAction, restoreContractAction } from '@/lib/contract-actions';

type Contract = components['schemas']['ContractRead'];
type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Contract — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: { created?: string; updated?: string; restored?: string; error?: string };
}

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 3 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

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
  return `${numFmt.format(n)} kg`;
}

export default async function ContractDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let contract: Contract | null = null;
  let me: UserRead | null = null;
  let suppliers: Supplier[] = [];
  let fetchError: string | null = null;

  try {
    [contract, me, suppliers] = await Promise.all([
      apiGet<Contract>(`/contracts/${id}`, { query: { include_deleted: true } }),
      apiGet<UserRead>('/auth/me'),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!contract) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            <Link href="/app/contracts" className="hover:text-ink">
              Contracts
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
  const isDeleted = !!contract.deleted_at;
  const supplier = contract.supplier_id
    ? suppliers.find((s) => s.id === contract!.supplier_id)
    : null;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/contracts" className="hover:text-ink">
            Contracts
          </Link>{' '}
          / {contract.code}
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">
            {contract.code}
            {isDeleted && (
              <span className="ml-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent">
                · deleted
              </span>
            )}
          </h1>
          {isAdmin && !isDeleted && (
            <div className="flex items-center gap-2">
              <Link
                href={`/app/contracts/${contract.id}/edit`}
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Edit
              </Link>
              <form action={deleteContractAction}>
                <input type="hidden" name="id" value={contract.id} />
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
            <form action={restoreContractAction}>
              <input type="hidden" name="id" value={contract.id} />
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
          {contract.is_placeholder ? 'placeholder' : 'real'}
          {supplier ? ` · ${supplier.code} ${supplier.name}` : ' · no supplier'}
        </p>
      </header>

      {searchParams.created === '1' && <Banner kind="ok">Contract created</Banner>}
      {searchParams.updated === '1' && <Banner kind="ok">Contract updated</Banner>}
      {searchParams.restored === '1' && <Banner kind="ok">Contract restored</Banner>}
      {searchParams.error && <Banner kind="err">{searchParams.error}</Banner>}

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DataBlock title="Identity">
          <Row label="Code">{contract.code}</Row>
          <Row label="Supplier">
            {supplier ? (
              <Link href={`/app/suppliers/${supplier.id}`} className="hover:text-ink">
                {supplier.code} · {supplier.name}
              </Link>
            ) : (
              '—'
            )}
          </Row>
          <Row label="Type">{contract.is_placeholder ? 'placeholder' : 'real'}</Row>
        </DataBlock>

        <DataBlock title="Period">
          <Row label="Start">{fmtDate(contract.start_date)}</Row>
          <Row label="End">{fmtDate(contract.end_date)}</Row>
          <Row label="Volume">{fmtKg(contract.total_kg_committed)}</Row>
        </DataBlock>

        {contract.notes && (
          <DataBlock title="Notes" full>
            <p className="font-mono text-[0.78rem] text-ink whitespace-pre-wrap">
              {contract.notes}
            </p>
          </DataBlock>
        )}

        <DataBlock title="Audit" full>
          <Row label="Created">{fmtDateTime(contract.created_at)}</Row>
          <Row label="Updated">{fmtDateTime(contract.updated_at)}</Row>
          <Row label="Deleted at">{fmtDateTime(contract.deleted_at)}</Row>
        </DataBlock>
      </section>
    </div>
  );
}

function Banner({ kind, children }: { kind: 'ok' | 'err'; children: React.ReactNode }) {
  const cls =
    kind === 'ok'
      ? 'border-olive-deep bg-olive-deep/5 text-olive-deep'
      : 'border-accent bg-accent/5 text-accent';
  return (
    <p
      role={kind === 'ok' ? 'status' : 'alert'}
      className={`mt-6 border ${cls} px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em]`}
    >
      {children}
    </p>
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
