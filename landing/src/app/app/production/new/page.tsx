import Link from 'next/link';
import { ProductionForm } from '../_components/production-form';
import { createProductionAction } from '@/lib/production-actions';

export const dynamic = 'force-dynamic';
export const metadata = { title: 'New production day — DFT' };

export default function NewProductionPage() {
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/production" className="hover:text-ink">
            Production
          </Link>{' '}
          / new
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          New production day
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Aggregated daily production breakdown. Date is the natural key (one row per day). Closure
          warning if input vs. sum differs by more than 1%.
        </p>
      </header>

      <div className="mt-6">
        <ProductionForm
          action={createProductionAction}
          initialValues={{ prod_date: today }}
          submitLabel="Save day"
          cancelHref="/app/production"
        />
      </div>
    </div>
  );
}
