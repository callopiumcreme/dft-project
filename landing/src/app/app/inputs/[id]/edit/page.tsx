import Link from 'next/link';
import { notFound } from 'next/navigation';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { InputForm } from '../../_components/input-form';
import { updateInputAction } from '@/lib/inputs-actions';

type Input = components['schemas']['DailyInputRead'];
type Supplier = components['schemas']['SupplierRead'];
type Certificate = components['schemas']['CertificateRead'];
type Contract = components['schemas']['ContractRead'];

export const dynamic = 'force-dynamic';
export const metadata = { title: 'Edit input — DFT' };

interface PageProps {
  params: { id: string };
}

function recordToFormValues(r: Input): Record<string, string> {
  return {
    entry_date: r.entry_date,
    entry_time: r.entry_time ? r.entry_time.slice(0, 5) : '',
    supplier_id: String(r.supplier_id),
    certificate_id: r.certificate_id ? String(r.certificate_id) : '',
    contract_id: r.contract_id ? String(r.contract_id) : '',
    ersv_number: r.ersv_number ?? '',
    car_kg: r.car_kg ?? '',
    truck_kg: r.truck_kg ?? '',
    special_kg: r.special_kg ?? '',
    theor_veg_pct: r.theor_veg_pct ?? '',
    manuf_veg_pct: r.manuf_veg_pct ?? '',
    c14_analysis: r.c14_analysis ?? '',
    c14_value: r.c14_value ?? '',
    notes: r.notes ?? '',
  };
}

export default async function EditInputPage({ params }: PageProps) {
  const id = Number.parseInt(params.id, 10);
  if (!Number.isInteger(id) || id <= 0) notFound();

  let input: Input | null = null;
  let suppliers: Supplier[] = [];
  let certificates: Certificate[] = [];
  let contracts: Contract[] = [];
  let fetchError: string | null = null;

  try {
    [input, suppliers, certificates, contracts] = await Promise.all([
      apiGet<Input>(`/daily-inputs/${id}`),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
      apiGet<Certificate[]>('/certificates', { query: { active_only: false } }),
      apiGet<Contract[]>('/contracts', { query: { active_only: false } }),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    fetchError = e instanceof ApiError ? `${e.status} · ${e.detail}` : 'unknown error';
  }

  if (!input) {
    return (
      <div className="mx-auto max-w-editorial">
        <header className="border-b border-rule pb-6">
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

  const boundAction = updateInputAction.bind(null, id);

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          <Link href="/app/inputs" className="hover:text-ink">
            Inputs
          </Link>{' '}
          /{' '}
          <Link href={`/app/inputs/${input.id}`} className="hover:text-ink">
            #{input.id}
          </Link>{' '}
          / edit
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Edit input #{input.id}
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {input.entry_date}
          {input.entry_time ? ` · ${input.entry_time}` : ''} · changes audit logged
        </p>
      </header>

      <div className="mt-6">
        <InputForm
          suppliers={supplierOpts}
          certificates={certOpts}
          contracts={contractOpts}
          action={boundAction}
          initialValues={recordToFormValues(input)}
          submitLabel="Save changes"
          cancelHref={`/app/inputs/${input.id}`}
        />
      </div>
    </div>
  );
}
