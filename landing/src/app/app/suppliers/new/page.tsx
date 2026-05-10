import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { SupplierForm } from '../_components/supplier-form';
import { createSupplierAction } from '@/lib/supplier-actions';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'New supplier — DFT' };

export default async function NewSupplierPage() {
  let me: UserRead;
  try {
    me = await apiGet<UserRead>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    throw e;
  }
  if (me.role !== 'admin') redirect('/app/suppliers?error=admin_required');

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/suppliers" className="hover:text-ink">
            Suppliers
          </Link>{' '}
          / new
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">New supplier</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Master data — admin only. Audit logged.
        </p>
      </header>

      <div className="mt-6">
        <SupplierForm
          action={createSupplierAction}
          initialValues={{ active: 'on' }}
          submitLabel="Create supplier"
          cancelHref="/app/suppliers"
        />
      </div>
    </div>
  );
}
