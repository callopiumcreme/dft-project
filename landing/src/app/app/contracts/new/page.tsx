import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { ContractForm } from '../_components/contract-form';
import { createContractAction } from '@/lib/contract-actions';

type UserRead = components['schemas']['UserRead'];
type Supplier = components['schemas']['SupplierRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'New contract — DFT' };

interface PageProps {
  searchParams: { supplier_id?: string };
}

export default async function NewContractPage({ searchParams }: PageProps) {
  let me: UserRead;
  let suppliers: Supplier[];
  try {
    [me, suppliers] = await Promise.all([
      apiGet<UserRead>('/auth/me'),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    throw e;
  }
  if (me.role !== 'admin') redirect('/app/contracts?error=admin_required');

  const presetSupplierId = searchParams.supplier_id ?? '';

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/contracts" className="hover:text-ink">
            Contracts
          </Link>{' '}
          / new
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">New contract</h1>
      </header>

      <div className="mt-6">
        <ContractForm
          action={createContractAction}
          suppliers={suppliers}
          initialValues={{ supplier_id: presetSupplierId }}
          submitLabel="Create"
          cancelHref="/app/contracts"
        />
      </div>
    </div>
  );
}
