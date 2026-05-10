'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { useRouter } from 'next/navigation';
import type { ContractFormState } from '@/lib/contract-actions';

export type FormValues = Record<string, string>;

export interface SupplierOption {
  id: number;
  code: string;
  name: string;
}

export interface ContractFormProps {
  action: (prev: ContractFormState, fd: FormData) => Promise<ContractFormState>;
  initialValues: FormValues;
  suppliers: SupplierOption[];
  submitLabel: string;
  cancelHref: string;
}

const initialState: ContractFormState = {};

function SubmitButton({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="border border-ink bg-ink px-5 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60"
    >
      {pending ? 'Saving…' : label}
    </button>
  );
}

export function ContractForm({
  action,
  initialValues,
  suppliers,
  submitLabel,
  cancelHref,
}: ContractFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const router = useRouter();

  const v: FormValues = { ...initialValues, ...(state.values ?? {}) };
  const fe = state.fieldErrors ?? {};

  const placeholderChecked =
    v.is_placeholder === 'on' || v.is_placeholder === 'true' || v.is_placeholder === '1';

  return (
    <form action={formAction} noValidate className="space-y-8">
      <Section title="Identity">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Code" name="code" error={fe.code} required>
            <input
              type="text"
              id="code"
              name="code"
              defaultValue={v.code ?? ''}
              required
              maxLength={32}
              placeholder="CTR-2026-01"
              className={inputCls(!!fe.code)}
            />
          </Field>
          <Field label="Supplier" name="supplier_id" error={fe.supplier_id}>
            <select
              id="supplier_id"
              name="supplier_id"
              defaultValue={v.supplier_id ?? ''}
              className={inputCls(!!fe.supplier_id)}
            >
              <option value="">— none —</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} · {s.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </Section>

      <Section title="Period">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Start date" name="start_date" error={fe.start_date}>
            <input
              type="date"
              id="start_date"
              name="start_date"
              defaultValue={v.start_date ?? ''}
              className={inputCls(!!fe.start_date)}
            />
          </Field>
          <Field label="End date" name="end_date" error={fe.end_date}>
            <input
              type="date"
              id="end_date"
              name="end_date"
              defaultValue={v.end_date ?? ''}
              className={inputCls(!!fe.end_date)}
            />
          </Field>
        </div>
      </Section>

      <Section title="Volume">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field
            label="Total kg committed"
            name="total_kg_committed"
            error={fe.total_kg_committed}
          >
            <input
              type="number"
              id="total_kg_committed"
              name="total_kg_committed"
              defaultValue={v.total_kg_committed ?? ''}
              min={0}
              step="0.001"
              placeholder="0"
              className={inputCls(!!fe.total_kg_committed)}
            />
          </Field>
          <div className="flex items-end">
            <label className="flex items-center gap-2 font-mono text-[0.78rem] text-ink">
              <input
                type="checkbox"
                name="is_placeholder"
                defaultChecked={placeholderChecked}
                className="h-4 w-4 border border-rule accent-ink"
              />
              <span>Placeholder (umbrella / unallocated)</span>
            </label>
          </div>
        </div>
      </Section>

      <Section title="Notes">
        <Field label="Notes" name="notes" error={fe.notes}>
          <textarea
            id="notes"
            name="notes"
            rows={4}
            defaultValue={v.notes ?? ''}
            maxLength={4000}
            className={inputCls(!!fe.notes) + ' resize-y'}
          />
        </Field>
      </Section>

      {state.error && (
        <p
          role="alert"
          className="border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-accent"
        >
          {state.error}
        </p>
      )}

      <div className="flex items-center gap-3 border-t border-rule pt-6">
        <SubmitButton label={submitLabel} />
        <button
          type="button"
          onClick={() => router.push(cancelHref)}
          className="border border-rule bg-bg-soft px-5 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft hover:border-ink hover:text-ink"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function inputCls(hasError: boolean): string {
  return [
    'w-full border bg-bg-soft px-2 py-1.5 font-mono text-[0.78rem] text-ink',
    hasError ? 'border-accent' : 'border-rule',
    'focus:outline-none focus:border-ink',
  ].join(' ');
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border border-rule bg-bg-soft p-5">
      <h2 className="mb-4 font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Field({
  label,
  name,
  error,
  required,
  children,
}: {
  label: string;
  name: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={name}
        className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute"
      >
        {label}
        {required && <span className="ml-1 text-accent">*</span>}
      </label>
      {children}
      {error && (
        <p className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-accent">{error}</p>
      )}
    </div>
  );
}
