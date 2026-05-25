import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { BuyerForm } from '../_components/buyer-form';
import { createBuyerAction } from '@/lib/buyer-actions';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'New buyer — DFT' };

export default async function NewBuyerPage() {
  let me: UserRead;
  try {
    me = await apiGet<UserRead>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    throw e;
  }
  if (me.role !== 'admin' && me.role !== 'operator') {
    redirect('/app/buyers?error=operator_required');
  }

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/buyers" className="hover:text-ink">
            Buyers
          </Link>{' '}
          / new
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">New buyer</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Master data — operator+ only. Audit logged.
        </p>
      </header>

      <div className="mt-6">
        <BuyerForm
          action={createBuyerAction}
          initialValues={{}}
          submitLabel="Create buyer"
          cancelHref="/app/buyers"
        />
      </div>
    </div>
  );
}
