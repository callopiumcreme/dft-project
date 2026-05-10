import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { ContractForm } from '../../_components/contract-form';
import { updateContractAction, type ContractFormState } from '@/lib/contract-actions';

type Contract = components['schemas']['ContractRead'];
type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Edit contract — DFT' };

interface PageProps {
  params: { id: string };
}

export default async function EditContractPage({ params }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let me: UserRead;
  let contract: Contract;
  let suppliers: Supplier[];
  try {
    [me, contract, suppliers] = await Promise.all([
      apiGet<UserRead>('/auth/me'),
      apiGet<Contract>(`/contracts/${id}`),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  if (me.role !== 'admin') redirect(`/app/contracts/${id}?error=admin_required`);

  const updateBound = updateContractAction.bind(null, contract.id) as (
    prev: ContractFormState,
    fd: FormData,
  ) => Promise<ContractFormState>;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/contracts" className="hover:text-ink">
            Contracts
          </Link>{' '}
          /{' '}
          <Link href={`/app/contracts/${contract.id}`} className="hover:text-ink">
            {contract.code}
          </Link>{' '}
          / edit
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Edit {contract.code}
        </h1>
      </header>

      <div className="mt-6">
        <ContractForm
          action={updateBound}
          suppliers={suppliers}
          initialValues={{
            code: contract.code,
            supplier_id: contract.supplier_id ? String(contract.supplier_id) : '',
            start_date: contract.start_date ?? '',
            end_date: contract.end_date ?? '',
            total_kg_committed: contract.total_kg_committed ?? '',
            is_placeholder: contract.is_placeholder ? 'on' : '',
            notes: contract.notes ?? '',
          }}
          submitLabel="Save changes"
          cancelHref={`/app/contracts/${contract.id}`}
        />
      </div>
    </div>
  );
}
