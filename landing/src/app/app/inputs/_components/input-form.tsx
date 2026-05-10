'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { InputFormState } from '@/lib/inputs-actions';

export type Option = { id: number; label: string; supplier_id?: number | null };

export type FormValues = Record<string, string>;

export interface InputFormProps {
  suppliers: Option[];
  certificates: Option[];
  contracts: Option[];
  action: (prev: InputFormState, fd: FormData) => Promise<InputFormState>;
  initialValues: FormValues;
  submitLabel: string;
  cancelHref: string;
}

const initialState: InputFormState = {};

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

export function InputForm({
  suppliers,
  certificates,
  contracts,
  action,
  initialValues,
  submitLabel,
  cancelHref,
}: InputFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const router = useRouter();

  const v: FormValues = { ...initialValues, ...(state.values ?? {}) };
  const fe = state.fieldErrors ?? {};

  const [supplierId, setSupplierId] = useState<string>(v.supplier_id ?? '');

  const filteredCerts = useMemo(() => {
    if (!supplierId) return certificates;
    const sid = Number(supplierId);
    return certificates.filter((c) => !c.supplier_id || c.supplier_id === sid);
  }, [supplierId, certificates]);

  const filteredContracts = useMemo(() => {
    if (!supplierId) return contracts;
    const sid = Number(supplierId);
    return contracts.filter((c) => !c.supplier_id || c.supplier_id === sid);
  }, [supplierId, contracts]);

  return (
    <form action={formAction} noValidate className="space-y-8">
      <Section title="Date & supplier">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Field label="Entry date" name="entry_date" error={fe.entry_date} required>
            <input
              type="date"
              id="entry_date"
              name="entry_date"
              defaultValue={v.entry_date ?? ''}
              required
              className={inputCls(!!fe.entry_date)}
            />
          </Field>
          <Field label="Entry time" name="entry_time" error={fe.entry_time}>
            <input
              type="time"
              id="entry_time"
              name="entry_time"
              defaultValue={v.entry_time ?? ''}
              className={inputCls(!!fe.entry_time)}
            />
          </Field>
          <Field label="Supplier" name="supplier_id" error={fe.supplier_id} required>
            <select
              id="supplier_id"
              name="supplier_id"
              defaultValue={v.supplier_id ?? ''}
              onChange={(e) => setSupplierId(e.currentTarget.value)}
              required
              className={inputCls(!!fe.supplier_id)}
            >
              <option value="">— select —</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Field label="Certificate" name="certificate_id" error={fe.certificate_id}>
            <select
              id="certificate_id"
              name="certificate_id"
              defaultValue={v.certificate_id ?? ''}
              className={inputCls(!!fe.certificate_id)}
            >
              <option value="">— optional —</option>
              {filteredCerts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Contract" name="contract_id" error={fe.contract_id}>
            <select
              id="contract_id"
              name="contract_id"
              defaultValue={v.contract_id ?? ''}
              className={inputCls(!!fe.contract_id)}
            >
              <option value="">— optional —</option>
              {filteredContracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="eRSV number" name="ersv_number" error={fe.ersv_number}>
            <input
              type="text"
              id="ersv_number"
              name="ersv_number"
              defaultValue={v.ersv_number ?? ''}
              placeholder="123/25"
              className={inputCls(!!fe.ersv_number)}
            />
          </Field>
        </div>
      </Section>

      <Section title="Input weights (kg)">
        <p className="mb-3 font-mono text-[0.7rem] text-ink-mute">
          At least one of car / truck / special must be &gt; 0.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Field label="Car kg" name="car_kg" error={fe.car_kg}>
            <input
              type="number"
              step="0.01"
              min="0"
              id="car_kg"
              name="car_kg"
              defaultValue={v.car_kg ?? ''}
              placeholder="0.00"
              className={inputCls(!!fe.car_kg)}
            />
          </Field>
          <Field label="Truck kg" name="truck_kg" error={fe.truck_kg}>
            <input
              type="number"
              step="0.01"
              min="0"
              id="truck_kg"
              name="truck_kg"
              defaultValue={v.truck_kg ?? ''}
              placeholder="0.00"
              className={inputCls(!!fe.truck_kg)}
            />
          </Field>
          <Field label="Special kg" name="special_kg" error={fe.special_kg}>
            <input
              type="number"
              step="0.01"
              min="0"
              id="special_kg"
              name="special_kg"
              defaultValue={v.special_kg ?? ''}
              placeholder="0.00"
              className={inputCls(!!fe.special_kg)}
            />
          </Field>
        </div>
      </Section>

      <Section title="Veg % & C14 analysis">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Theor. veg %" name="theor_veg_pct" error={fe.theor_veg_pct}>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              id="theor_veg_pct"
              name="theor_veg_pct"
              defaultValue={v.theor_veg_pct ?? ''}
              placeholder="0.00"
              className={inputCls(!!fe.theor_veg_pct)}
            />
          </Field>
          <Field label="Manuf. veg %" name="manuf_veg_pct" error={fe.manuf_veg_pct}>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              id="manuf_veg_pct"
              name="manuf_veg_pct"
              defaultValue={v.manuf_veg_pct ?? ''}
              placeholder="0.00"
              className={inputCls(!!fe.manuf_veg_pct)}
            />
          </Field>
          <Field label="C14 analysis (lab / sample / dates)" name="c14_analysis" error={fe.c14_analysis}>
            <textarea
              id="c14_analysis"
              name="c14_analysis"
              rows={2}
              defaultValue={v.c14_analysis ?? ''}
              placeholder="SAYBOLT · sample NLADM-25-... · sampled 2025-03-18"
              className={inputCls(!!fe.c14_analysis) + ' resize-y'}
            />
          </Field>
          <Field label="C14 value" name="c14_value" error={fe.c14_value}>
            <input
              type="number"
              step="0.001"
              id="c14_value"
              name="c14_value"
              defaultValue={v.c14_value ?? ''}
              placeholder="0.293"
              className={inputCls(!!fe.c14_value)}
            />
          </Field>
        </div>
      </Section>

      <Section title="Notes">
        <Field label="Notes" name="notes" error={fe.notes}>
          <textarea
            id="notes"
            name="notes"
            rows={3}
            defaultValue={v.notes ?? ''}
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
        <p className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-accent">
          {error}
        </p>
      )}
    </div>
  );
}
