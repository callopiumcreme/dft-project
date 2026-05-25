import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deleteBuyerAction } from '@/lib/buyer-actions';

interface Buyer {
  id: number;
  name: string;
  country: string | null;
  vat: string | null;
  contact: string | null;
  notes: string | null;
  created_at: string;
}

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Buyer — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: { created?: string; updated?: string; error?: string };
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-GB');
}

export default async function BuyerDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let buyer: Buyer | null = null;
  let me: UserRead | null = null;
  let fetchError: string | null = null;

  try {
    [buyer, me] = await Promise.all([
      apiGet<Buyer>(`/byproduct/buyers/${id}`),
      apiGet<UserRead>('/auth/me'),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!buyer) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            <Link href="/app/buyers" className="hover:text-ink">
              Buyers
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

  const role = me?.role;
  const canEdit = role === 'admin' || role === 'operator';
  const isAdmin = role === 'admin';

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/buyers" className="hover:text-ink">
            Buyers
          </Link>{' '}
          / {buyer.name}
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">{buyer.name}</h1>
          <div className="flex items-center gap-2">
            {canEdit && (
              <Link
                href={`/app/buyers/${buyer.id}/edit`}
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Edit
              </Link>
            )}
            {isAdmin && (
              <form action={deleteBuyerAction}>
                <input type="hidden" name="id" value={buyer.id} />
                <button
                  type="submit"
                  className="border border-accent px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent hover:bg-accent/10"
                >
                  Delete
                </button>
              </form>
            )}
          </div>
        </div>
        <p className="mt-3 font-mono text-[0.72rem] text-ink-soft">
          {buyer.country ?? '—'}
          {buyer.vat ? ` · VAT ${buyer.vat}` : ''}
        </p>
      </header>

      {searchParams.created === '1' && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Buyer created
        </p>
      )}
      {searchParams.updated === '1' && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Buyer updated
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
          <Row label="Name">{buyer.name}</Row>
          <Row label="Country">{buyer.country ?? '—'}</Row>
          <Row label="VAT / Tax ID">{buyer.vat ?? '—'}</Row>
        </DataBlock>

        <DataBlock title="Contact">
          <Row label="Contact">{buyer.contact ?? '—'}</Row>
        </DataBlock>

        {buyer.notes && (
          <DataBlock title="Notes" full>
            <p className="font-mono text-[0.78rem] text-ink whitespace-pre-wrap">{buyer.notes}</p>
          </DataBlock>
        )}

        <DataBlock title="Audit" full>
          <Row label="Created">{fmtDateTime(buyer.created_at)}</Row>
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
