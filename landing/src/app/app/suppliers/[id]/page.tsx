import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deleteSupplierAction, restoreSupplierAction } from '@/lib/supplier-actions';

type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Supplier — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: { created?: string; updated?: string; restored?: string; error?: string };
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-GB');
}

export default async function SupplierDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let supplier: Supplier | null = null;
  let me: UserRead | null = null;
  let fetchError: string | null = null;

  try {
    [supplier, me] = await Promise.all([
      apiGet<Supplier>(`/suppliers/${id}`, { query: { include_deleted: true } }),
      apiGet<UserRead>('/auth/me'),
    ]);
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
