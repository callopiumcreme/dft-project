import Link from 'next/link';
import { redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { createCertificateAction } from '@/lib/certificate-actions';
import CertificateForm from '../_components/certificate-form';

type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

export default async function NewCertificatePage() {
  let me: UserRead | null = null;
  let suppliers: Supplier[] = [];

  try {
    [me, suppliers] = await Promise.all([
      apiGet<UserRead>('/auth/me'),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
  }

  if (!me || me.role !== 'admin') {
    return (
      <div className="mx-auto max-w-editorial">
        <p className="border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent">
          Admin role required.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Master data ·{' '}
          <Link href="/app/certificates" className="hover:text-ink">
            Certificates
          </Link>
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          New certificate
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Register an ISCC EU (or other scheme) certificate. Mark as placeholder if the document is
          not yet on file. Link the suppliers it covers.
        </p>
      </header>

      <CertificateForm
        action={createCertificateAction}
        suppliers={suppliers}
        submitLabel="Create certificate"
        cancelHref="/app/certificates"
      />
    </div>
  );
}
