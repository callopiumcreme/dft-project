import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { ProductionForm } from '../../_components/production-form';
import { updateProductionAction } from '@/lib/production-actions';

type Production = components['schemas']['DailyProductionRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Edit production day — DFT' };

interface PageProps {
  params: { id: string };
}

function recordToFormValues(r: Production): Record<string, string> {
  return {
    prod_date: r.prod_date,
    kg_to_production: r.kg_to_production ?? '',
    eu_prod_kg: r.eu_prod_kg ?? '',
    plus_prod_kg: r.plus_prod_kg ?? '',
    carbon_black_kg: r.carbon_black_kg ?? '',
    metal_scrap_kg: r.metal_scrap_kg ?? '',
    h2o_kg: r.h2o_kg ?? '',
    gas_syngas_kg: r.gas_syngas_kg ?? '',
    losses_kg: r.losses_kg ?? '',
    output_eu_kg: r.output_eu_kg ?? '',
    contract_ref: r.contract_ref ?? '',
    pos_number: r.pos_number ?? '',
    notes: r.notes ?? '',
  };
}

export default async function EditProductionPage({ params }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let prod: Production | null = null;
  let fetchError: string | null = null;

  try {
    prod = await apiGet<Production>(`/daily-production/${id}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!prod) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
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

  const boundAction = updateProductionAction.bind(null, id);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/production" className="hover:text-ink">
            Production
          </Link>{' '}
          /{' '}
          <Link href={`/app/production/${prod.id}`} className="hover:text-ink">
            {prod.prod_date}
          </Link>{' '}
          / edit
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Edit {prod.prod_date}
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Changes audit logged. Production date is the natural key and cannot be changed.
        </p>
      </header>

      <div className="mt-6">
        <ProductionForm
          action={boundAction}
          initialValues={recordToFormValues(prod)}
          submitLabel="Save changes"
          cancelHref={`/app/production/${prod.id}`}
          lockDate
        />
      </div>
    </div>
  );
}
