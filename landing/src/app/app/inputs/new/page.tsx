import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { InputForm } from './input-form';

type Supplier = components['schemas']['SupplierRead'];
type Certificate = components['schemas']['CertificateRead'];
type Contract = components['schemas']['ContractRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'New input — DFT' };

export default async function NewInputPage() {
  let suppliers: Supplier[] = [];
  let certificates: Certificate[] = [];
  let contracts: Contract[] = [];
  let fetchError: string | null = null;

  try {
    [suppliers, certificates, contracts] = await Promise.all([
      apiGet<Supplier[]>('/suppliers', { query: { active_only: true } }),
      apiGet<Certificate[]>('/certificates', { query: { active_only: true } }),
      apiGet<Contract[]>('/contracts', { query: { active_only: true } }),
    ]);
  } catch (e) {
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  const supplierOpts = suppliers
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((s) => ({ id: s.id, label: `${s.code} · ${s.name}` }));

  const certOpts = certificates
    .slice()
    .sort((a, b) => a.cert_number.localeCompare(b.cert_number))
    .map((c) => ({
      id: c.id,
      label: `${c.cert_number} · ${c.scheme ?? '—'}`,
      supplier_id: null,
    }));

  const contractOpts = contracts
    .slice()
    .sort((a, b) => a.code.localeCompare(b.code))
    .map((c) => ({
      id: c.id,
      label: c.code,
      supplier_id: c.supplier_id ?? null,
    }));

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/inputs" className="hover:text-ink">
            Inputs
          </Link>{' '}
          / new
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">New input</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Per-vehicle input weights with supplier, certificate, contract references. Audit logged.
        </p>
      </header>

      {fetchError && (
        <div className="mt-6 border border-accent bg-accent/5 p-4 font-mono text-[0.75rem] text-accent">
          Cannot load select options: {fetchError}
        </div>
      )}

      <div className="mt-6">
        <InputForm
          suppliers={supplierOpts}
          certificates={certOpts}
          contracts={contractOpts}
          defaultDate={today}
        />
      </div>
    </div>
  );
}
