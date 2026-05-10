import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { SupplierForm } from '../../_components/supplier-form';
import { updateSupplierAction, type SupplierFormState } from '@/lib/supplier-actions';

type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Edit supplier — DFT' };

interface PageProps {
  params: { id: string };
}

export default async function EditSupplierPage({ params }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let me: UserRead;
  let supplier: Supplier;
  try {
    [me, supplier] = await Promise.all([
      apiGet<UserRead>('/auth/me'),
      apiGet<Supplier>(`/suppliers/${id}`),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  if (me.role !== 'admin') redirect(`/app/suppliers/${id}?error=admin_required`);

  const updateBound = updateSupplierAction.bind(null, supplier.id) as (
    prev: SupplierFormState,
    fd: FormData,
  ) => Promise<SupplierFormState>;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/suppliers" className="hover:text-ink">
            Suppliers
          </Link>{' '}
          /{' '}
          <Link href={`/app/suppliers/${supplier.id}`} className="hover:text-ink">
            {supplier.code}
          </Link>{' '}
          / edit
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Edit {supplier.name}
        </h1>
      </header>

      <div className="mt-6">
        <SupplierForm
          action={updateBound}
          initialValues={{
            name: supplier.name,
            code: supplier.code,
            country: supplier.country ?? '',
            active: supplier.active ? 'on' : '',
            is_aggregate: supplier.is_aggregate ? 'on' : '',
            notes: supplier.notes ?? '',
          }}
          submitLabel="Save changes"
          cancelHref={`/app/suppliers/${supplier.id}`}
        />
      </div>
    </div>
  );
}
