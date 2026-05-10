'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { useRouter } from 'next/navigation';
import type { SupplierFormState } from '@/lib/supplier-actions';

export type FormValues = Record<string, string>;

export interface SupplierFormProps {
  action: (prev: SupplierFormState, fd: FormData) => Promise<SupplierFormState>;
  initialValues: FormValues;
  submitLabel: string;
  cancelHref: string;
}

const initialState: SupplierFormState = {};

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

export function SupplierForm({
  action,
  initialValues,
  submitLabel,
  cancelHref,
}: SupplierFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const router = useRouter();

  const v: FormValues = { ...initialValues, ...(state.values ?? {}) };
  const fe = state.fieldErrors ?? {};

  const activeChecked = v.active === undefined ? true : v.active === 'on' || v.active === 'true' || v.active === '1';
  const aggregateChecked = v.is_aggregate === 'on' || v.is_aggregate === 'true' || v.is_aggregate === '1';

  return (
    <form action={formAction} noValidate className="space-y-8">
      <Section title="Identity">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Name" name="name" error={fe.name} required>
            <input
              type="text"
              id="name"
              name="name"
              defaultValue={v.name ?? ''}
              required
              maxLength={200}
              className={inputCls(!!fe.name)}
            />
          </Field>
          <Field label="Code" name="code" error={fe.code} required>
            <input
              type="text"
              id="code"
              name="code"
              defaultValue={v.code ?? ''}
              required
              maxLength={32}
              placeholder="ABC-01"
              className={inputCls(!!fe.code)}
            />
          </Field>
          <Field label="Country" name="country" error={fe.country}>
            <input
              type="text"
              id="country"
              name="country"
              defaultValue={v.country ?? ''}
              maxLength={80}
              placeholder="NL · IT · …"
              className={inputCls(!!fe.country)}
            />
          </Field>
        </div>
      </Section>

      <Section title="Status">
        <div className="flex flex-wrap gap-6 font-mono text-[0.78rem] text-ink">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              name="active"
              defaultChecked={activeChecked}
              className="h-4 w-4 border border-rule accent-ink"
            />
            <span>Active</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              name="is_aggregate"
              defaultChecked={aggregateChecked}
              className="h-4 w-4 border border-rule accent-ink"
            />
            <span>Aggregate (umbrella supplier)</span>
          </label>
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
        <p className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-accent">
          {error}
        </p>
      )}
    </div>
  );
}
