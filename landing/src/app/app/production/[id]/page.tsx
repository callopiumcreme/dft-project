import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deleteProductionAction } from '@/lib/production-actions';

type Production = components['schemas']['DailyProductionRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Production day — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: { updated?: string; error?: string };
}

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(n);
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-GB');
}

const PROD_KEYS: Array<[keyof Production, string]> = [
  ['eu_prod_kg', 'EU prod'],
  ['plus_prod_kg', 'Plus prod'],
  ['carbon_black_kg', 'Carbon black'],
  ['metal_scrap_kg', 'Metal scrap'],
  ['h2o_kg', 'H₂O'],
  ['gas_syngas_kg', 'Gas/syngas'],
  ['losses_kg', 'Losses'],
];

export default async function ProductionDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let prod: Production | null = null;
  let fetchError: string | null = null;

  try {
    prod = await apiGet<Production>(`/daily-production/${id}`, {
      query: { include_deleted: true },
    });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!prod) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            <Link href="/app/production" className="hover:text-ink">
              Production
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

  const isDeleted = !!prod.deleted_at;

  const inputKg = Number(prod.kg_to_production ?? 0);
  const sumKg = PROD_KEYS.reduce((s, [k]) => s + Number((prod as Production)[k] ?? 0), 0);
  const diff = sumKg - inputKg;
  const pct = inputKg > 0 ? (diff / inputKg) * 100 : 0;
  const balanced = inputKg > 0 && Math.abs(pct) <= 1;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/production" className="hover:text-ink">
            Production
          </Link>{' '}
          / {prod.prod_date}
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">
            {prod.prod_date}
            {isDeleted && (
              <span className="ml-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent">
                · deleted
              </span>
            )}
          </h1>
          {!isDeleted && (
            <div className="flex items-center gap-2">
              <Link
                href={`/app/production/${prod.id}/edit`}
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Edit
              </Link>
              <form action={deleteProductionAction}>
                <input type="hidden" name="id" value={prod.id} />
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
          Input {fmtKg(prod.kg_to_production)} kg · output {fmtKg(prod.output_eu_kg)} kg
          {prod.contract_ref ? ` · ${prod.contract_ref}` : ''}
        </p>
      </header>

      {searchParams.updated === '1' && (
        <p
          role="status"
          className="mt-6 border border-olive-deep bg-olive-deep/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-olive-deep"
        >
          Production day updated
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

      {inputKg > 0 && (
        <section
          className={`mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 border px-3 py-2 font-mono text-[0.72rem] ${
            balanced
              ? 'border-olive-deep bg-olive-deep/5 text-olive-deep'
              : 'border-accent bg-accent/5 text-accent'
          }`}
        >
          <div>
            <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Input</p>
            <p className="mt-0.5">{fmtKg(inputKg)} kg</p>
          </div>
          <div>
            <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Sum</p>
            <p className="mt-0.5">{fmtKg(sumKg)} kg</p>
          </div>
          <div>
            <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Diff</p>
            <p className="mt-0.5">
              {diff >= 0 ? '+' : ''}
              {fmtKg(diff)} kg ({pct.toFixed(2)}%)
            </p>
          </div>
          <div>
            <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Status</p>
            <p className="mt-0.5 uppercase tracking-[0.12em]">
              {balanced ? 'Balanced' : 'Imbalance'}
            </p>
          </div>
        </section>
      )}

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DataBlock title="Input">
          <Row label="kg to production">{fmtKg(prod.kg_to_production)}</Row>
        </DataBlock>

        <DataBlock title="Output">
          <Row label="EU output" emphasize>
            {fmtKg(prod.output_eu_kg)}
          </Row>
          <Row label="Contract">{prod.contract_ref ?? '—'}</Row>
          <Row label="POS">{prod.pos_number ?? '—'}</Row>
        </DataBlock>

        <DataBlock title="Production breakdown" full>
          {PROD_KEYS.map(([k, label]) => (
            <Row key={k as string} label={label}>
              {fmtKg((prod as Production)[k] as string | null | undefined)}
            </Row>
          ))}
        </DataBlock>

        {prod.notes && (
          <DataBlock title="Notes" full>
            <p className="font-mono text-[0.78rem] text-ink whitespace-pre-wrap">{prod.notes}</p>
          </DataBlock>
        )}

        <DataBlock title="Audit" full>
          <Row label="Created">
            {fmtDateTime(prod.created_at)}
            {prod.created_by ? ` · user #${prod.created_by}` : ''}
          </Row>
          <Row label="Updated">
            {fmtDateTime(prod.updated_at)}
            {prod.updated_by ? ` · user #${prod.updated_by}` : ''}
          </Row>
          {prod.source_file && (
            <Row label="Source">
              {prod.source_file}
              {prod.source_row !== null && prod.source_row !== undefined
                ? ` · row ${prod.source_row}`
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
      <dt className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
        {label}
      </dt>
      <dd
        className={`font-mono text-[0.78rem] ${emphasize ? 'text-ink font-medium' : 'text-ink-soft'} text-right`}
      >
        {children}
      </dd>
    </div>
  );
}
