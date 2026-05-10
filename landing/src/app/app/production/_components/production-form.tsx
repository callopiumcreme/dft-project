'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { ProductionFormState } from '@/lib/production-actions';

export type FormValues = Record<string, string>;

export interface ProductionFormProps {
  action: (prev: ProductionFormState, fd: FormData) => Promise<ProductionFormState>;
  initialValues: FormValues;
  submitLabel: string;
  cancelHref: string;
  lockDate?: boolean;
}

const initialState: ProductionFormState = {};

const PROD_FIELDS = [
  'eu_prod_kg',
  'plus_prod_kg',
  'carbon_black_kg',
  'metal_scrap_kg',
  'h2o_kg',
  'gas_syngas_kg',
  'losses_kg',
] as const;

function num(v: string | undefined): number {
  if (!v) return 0;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(n);
}

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

export function ProductionForm({
  action,
  initialValues,
  submitLabel,
  cancelHref,
  lockDate,
}: ProductionFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const router = useRouter();

  const v: FormValues = { ...initialValues, ...(state.values ?? {}) };
  const fe = state.fieldErrors ?? {};

  const [vals, setVals] = useState<FormValues>(v);

  const closure = useMemo(() => {
    const input = num(vals.kg_to_production);
    const sum = PROD_FIELDS.reduce((s, f) => s + num(vals[f]), 0);
    if (input <= 0) return null;
    const diff = sum - input;
    const pct = (diff / input) * 100;
    return { input, sum, diff, pct };
  }, [vals]);

  const onChange = (name: string, value: string) => {
    setVals((prev) => ({ ...prev, [name]: value }));
  };

  return (
    <form action={formAction} noValidate className="space-y-8">
      <Section title="Production date">
        <Field label="Production date" name="prod_date" error={fe.prod_date} required>
          <input
            type="date"
            id="prod_date"
            name="prod_date"
            defaultValue={v.prod_date ?? ''}
            required
            readOnly={lockDate}
            className={inputCls(!!fe.prod_date) + (lockDate ? ' bg-bg cursor-not-allowed' : '')}
            onChange={(e) => onChange('prod_date', e.currentTarget.value)}
          />
          {lockDate && (
            <p className="mt-1 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-ink-mute">
              Date is the natural key — cannot be changed after creation.
            </p>
          )}
        </Field>
      </Section>

      <Section title="Input to production">
        <Field label="kg to production" name="kg_to_production" error={fe.kg_to_production}>
          <input
            type="number"
            step="0.01"
            min="0"
            id="kg_to_production"
            name="kg_to_production"
            defaultValue={v.kg_to_production ?? ''}
            placeholder="0.00"
            className={inputCls(!!fe.kg_to_production)}
            onChange={(e) => onChange('kg_to_production', e.currentTarget.value)}
          />
        </Field>
      </Section>

      <Section title="Production breakdown (kg)">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {PROD_FIELDS.map((f) => (
            <Field key={f} label={LABELS[f]} name={f} error={fe[f]}>
              <input
                type="number"
                step="0.01"
                min="0"
                id={f}
                name={f}
                defaultValue={v[f] ?? ''}
                placeholder="0.00"
                className={inputCls(!!fe[f])}
                onChange={(e) => onChange(f, e.currentTarget.value)}
              />
            </Field>
          ))}
        </div>

        {closure && (
          <ClosurePanel
            input={closure.input}
            sum={closure.sum}
            diff={closure.diff}
            pct={closure.pct}
          />
        )}
      </Section>

      <Section title="Output & contract">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Field label="Output EU kg" name="output_eu_kg" error={fe.output_eu_kg}>
            <input
              type="number"
              step="0.01"
              min="0"
              id="output_eu_kg"
              name="output_eu_kg"
              defaultValue={v.output_eu_kg ?? ''}
              placeholder="0.00"
              className={inputCls(!!fe.output_eu_kg)}
            />
          </Field>
          <Field label="Contract ref" name="contract_ref" error={fe.contract_ref}>
            <input
              type="text"
              id="contract_ref"
              name="contract_ref"
              defaultValue={v.contract_ref ?? ''}
              placeholder="contract code"
              className={inputCls(!!fe.contract_ref)}
            />
          </Field>
          <Field label="POS number" name="pos_number" error={fe.pos_number}>
            <input
              type="text"
              id="pos_number"
              name="pos_number"
              defaultValue={v.pos_number ?? ''}
              placeholder="POS / batch"
              className={inputCls(!!fe.pos_number)}
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

const LABELS: Record<(typeof PROD_FIELDS)[number], string> = {
  eu_prod_kg: 'EU prod kg',
  plus_prod_kg: 'Plus prod kg',
  carbon_black_kg: 'Carbon black kg',
  metal_scrap_kg: 'Metal scrap kg',
  h2o_kg: 'H₂O kg',
  gas_syngas_kg: 'Gas/syngas kg',
  losses_kg: 'Losses kg',
};

function ClosurePanel({
  input,
  sum,
  diff,
  pct,
}: {
  input: number;
  sum: number;
  diff: number;
  pct: number;
}) {
  const abs = Math.abs(pct);
  const status =
    abs <= 0.5 ? 'ok' : abs <= 1 ? 'tight' : 'warn';
  const label = status === 'ok' ? 'Balanced' : status === 'tight' ? 'Within tolerance' : 'Imbalance';
  const tone =
    status === 'warn'
      ? 'border-accent bg-accent/5 text-accent'
      : status === 'tight'
        ? 'border-rule bg-bg-soft text-ink-soft'
        : 'border-olive-deep bg-olive-deep/5 text-olive-deep';

  return (
    <div
      className={`mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 border ${tone} px-3 py-2 font-mono text-[0.72rem]`}
    >
      <div>
        <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Input</p>
        <p className="mt-0.5">{fmt(input)} kg</p>
      </div>
      <div>
        <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Sum</p>
        <p className="mt-0.5">{fmt(sum)} kg</p>
      </div>
      <div>
        <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Diff</p>
        <p className="mt-0.5">
          {diff >= 0 ? '+' : ''}
          {fmt(diff)} kg ({pct.toFixed(2)}%)
        </p>
      </div>
      <div>
        <p className="text-[0.6rem] uppercase tracking-[0.14em] opacity-70">Status</p>
        <p className="mt-0.5 uppercase tracking-[0.12em]">{label}</p>
      </div>
    </div>
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
