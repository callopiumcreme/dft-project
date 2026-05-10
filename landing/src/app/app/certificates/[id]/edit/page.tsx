import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import {
  updateCertificateAction,
  type CertificateFormState,
} from '@/lib/certificate-actions';
import CertificateForm from '../../_components/certificate-form';

type Certificate = components['schemas']['CertificateRead'];
type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

interface PageProps {
  params: { id: string };
}

export default async function EditCertificatePage({ params }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let cert: Certificate | null = null;
  let me: UserRead | null = null;
  let suppliers: Supplier[] = [];

  try {
    [cert, me, suppliers] = await Promise.all([
      apiGet<Certificate>(`/certificates/${id}`),
      apiGet<UserRead>('/auth/me'),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/login');
    if (e instanceof ApiError && e.status === 404) notFound();
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
  if (!cert) notFound();

  const certId = cert.id;
  const boundAction = async (
    prev: CertificateFormState,
    fd: FormData,
  ): Promise<CertificateFormState> => {
    'use server';
    return updateCertificateAction(certId, prev, fd);
  };

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Master data ·{' '}
          <Link href="/app/certificates" className="hover:text-ink">
            Certificates
          </Link>{' '}
          /{' '}
          <Link href={`/app/certificates/${cert.id}`} className="hover:text-ink">
            {cert.cert_number}
          </Link>
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Edit certificate
        </h1>
      </header>

      <CertificateForm
        action={boundAction}
        suppliers={suppliers}
        initial={cert}
        submitLabel="Save changes"
        cancelHref={`/app/certificates/${cert.id}`}
      />
    </div>
  );
}
