import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { BuyerForm } from '../../_components/buyer-form';
import { updateBuyerAction, type BuyerFormState } from '@/lib/buyer-actions';

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
export const metadata = { title: 'Edit buyer — DFT' };

interface PageProps {
  params: { id: string };
}

export default async function EditBuyerPage({ params }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let me: UserRead;
  let buyer: Buyer;
  try {
    [me, buyer] = await Promise.all([
      apiGet<UserRead>('/auth/me'),
      apiGet<Buyer>(`/byproduct/buyers/${id}`),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  if (me.role !== 'admin' && me.role !== 'operator') {
    redirect(`/app/buyers/${id}?error=operator_required`);
  }

  const updateBound = updateBuyerAction.bind(null, buyer.id) as (
    prev: BuyerFormState,
    fd: FormData,
  ) => Promise<BuyerFormState>;

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/buyers" className="hover:text-ink">
            Buyers
          </Link>{' '}
          /{' '}
          <Link href={`/app/buyers/${buyer.id}`} className="hover:text-ink">
            {buyer.name}
          </Link>{' '}
          / edit
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Edit {buyer.name}
        </h1>
      </header>

      <div className="mt-6">
        <BuyerForm
          action={updateBound}
          initialValues={{
            name: buyer.name,
            country: buyer.country ?? '',
            vat: buyer.vat ?? '',
            contact: buyer.contact ?? '',
            notes: buyer.notes ?? '',
          }}
          submitLabel="Save changes"
          cancelHref={`/app/buyers/${buyer.id}`}
        />
      </div>
    </div>
  );
}
