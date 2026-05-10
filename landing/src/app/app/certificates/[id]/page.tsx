import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { deleteCertificateAction, restoreCertificateAction } from '@/lib/certificate-actions';

type Certificate = components['schemas']['CertificateRead'];
type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];
type Status = 'active' | 'expired' | 'revoked' | 'placeholder';

const STATUS_LABEL: Record<Status, string> = {
  active: 'Active',
  expired: 'Expired',
  revoked: 'Revoked',
  placeholder: 'Placeholder',
};

const STATUS_PILL: Record<Status, string> = {
  active: 'border-olive-deep bg-olive-deep/10 text-olive-deep',
  expired: 'border-accent bg-bg text-accent',
  revoked: 'border-ink-mute bg-bg text-ink-mute',
  placeholder: 'border-rule bg-bg text-ink-soft',
};

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Certificate — DFT' };

interface PageProps {
  params: { id: string };
  searchParams: { created?: string; updated?: string; restored?: string; error?: string };
}

const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  return new Date(v).toLocaleString('en-GB');
}

function asStatus(v: string): Status {
  return (['active', 'expired', 'revoked', 'placeholder'] as const).includes(v as Status)
    ? (v as Status)
    : 'placeholder';
}

export default async function CertificateDetailPage({ params, searchParams }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let cert: Certificate | null = null;
  let me: UserRead | null = null;
  let suppliers: Supplier[] = [];
  let fetchError: string | null = null;

  try {
    [cert, me, suppliers] = await Promise.all([
      apiGet<Certificate>(`/certificates/${id}`, { query: { include_deleted: true } }),
      apiGet<UserRead>('/auth/me'),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!cert) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            <Link href="/app/certificates" className="hover:text-ink">
              Certificates
            </Link>{' '}
            / #{id}
          </p>
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

  const isAdmin = me?.role === 'admin';
  const isDeleted = !!cert.deleted_at;
  const status = asStatus(cert.status);
  const linkedSuppliers = suppliers.filter((s) => cert!.supplier_ids.includes(s.id));

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/certificates" className="hover:text-ink">
            Certificates
          </Link>{' '}
          / {cert.cert_number}
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">
            {cert.cert_number}
            {isDeleted && (
              <span className="ml-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent">
                · deleted
              </span>
            )}
          </h1>
          {isAdmin && !isDeleted && (
            <div className="flex items-center gap-2">
              <Link
                href={`/app/certificates/${cert.id}/edit`}
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Edit
              </Link>
              <form action={deleteCertificateAction}>
                <input type="hidden" name="id" value={cert.id} />
                <button
                  type="submit"
                  className="border border-accent px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent hover:bg-accent/10"
                >
                  Delete
                </button>
              </form>
            </div>
          )}
          {isAdmin && isDeleted && (
            <form action={restoreCertificateAction}>
              <input type="hidden" name="id" value={cert.id} />
              <button
                type="submit"
                className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
              >
                Restore
              </button>
            </form>
          )}
        </div>
        <p className="mt-3 font-mono text-[0.72rem] text-ink-soft">
          <span
            className={`mr-2 inline-block border px-2 py-0.5 text-[0.65rem] uppercase ${STATUS_PILL[status]}`}
          >
            {STATUS_LABEL[status]}
          </span>
          {cert.scheme}
          {cert.is_placeholder ? ' · placeholder' : ''}
        </p>
      </header>

      {searchParams.created === '1' && <Banner kind="ok">Certificate created</Banner>}
      {searchParams.updated === '1' && <Banner kind="ok">Certificate updated</Banner>}
      {searchParams.restored === '1' && <Banner kind="ok">Certificate restored</Banner>}
      {searchParams.error && <Banner kind="err">{searchParams.error}</Banner>}

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DataBlock title="Identity">
          <Row label="Number">{cert.cert_number}</Row>
          <Row label="Scheme">{cert.scheme}</Row>
          <Row label="Status">{STATUS_LABEL[status]}</Row>
          <Row label="Type">{cert.is_placeholder ? 'placeholder' : 'real'}</Row>
        </DataBlock>

        <DataBlock title="Validity">
          <Row label="Issued at">{fmtDate(cert.issued_at)}</Row>
          <Row label="Expires at">{fmtDate(cert.expires_at)}</Row>
        </DataBlock>

        <DataBlock title="Suppliers covered" full>
          {linkedSuppliers.length === 0 ? (
            <p className="font-mono text-[0.78rem] text-ink-mute">No suppliers linked.</p>
          ) : (
            <ul className="space-y-1.5">
              {linkedSuppliers.map((s) => (
                <li
                  key={s.id}
                  className="flex items-baseline justify-between gap-3 border-b border-rule/40 pb-1.5 last:border-b-0 last:pb-0"
                >
                  <Link
                    href={`/app/suppliers/${s.id}`}
                    className="font-mono text-[0.78rem] text-ink hover:text-ink-soft"
                  >
                    {s.code} · {s.name}
                  </Link>
                  <span className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
                    {s.country ?? '—'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </DataBlock>

        {cert.document_url && (
          <DataBlock title="Document" full>
            <a
              href={cert.document_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[0.78rem] text-ink underline hover:text-ink-soft break-all"
            >
              {cert.document_url}
            </a>
          </DataBlock>
        )}

        {cert.notes && (
          <DataBlock title="Notes" full>
            <p className="font-mono text-[0.78rem] text-ink whitespace-pre-wrap">{cert.notes}</p>
          </DataBlock>
        )}

        <DataBlock title="Audit" full>
          <Row label="Created">{fmtDateTime(cert.created_at)}</Row>
          <Row label="Updated">{fmtDateTime(cert.updated_at)}</Row>
          <Row label="Deleted at">{fmtDateTime(cert.deleted_at)}</Row>
        </DataBlock>
      </section>
    </div>
  );
}

function Banner({ kind, children }: { kind: 'ok' | 'err'; children: React.ReactNode }) {
  const cls =
    kind === 'ok'
      ? 'border-olive-deep bg-olive-deep/5 text-olive-deep'
      : 'border-accent bg-accent/5 text-accent';
  return (
    <p
      role={kind === 'ok' ? 'status' : 'alert'}
      className={`mt-6 border ${cls} px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em]`}
    >
      {children}
    </p>
  );
}

function DataBlock({
  title,
  children,
  full,
}: {
  title: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <section className={`border border-rule bg-bg-soft p-5 ${full ? 'sm:col-span-2' : ''}`}>
      <h2 className="mb-3 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
        {title}
      </h2>
      <dl className="space-y-1.5">{children}</dl>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-rule/40 pb-1.5 last:border-b-0 last:pb-0">
      <dt className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
        {label}
      </dt>
      <dd className="font-mono text-[0.78rem] text-ink-soft text-right">{children}</dd>
    </div>
  );
}
