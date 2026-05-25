'use client';

import { useFormState, useFormStatus } from 'react-dom';
import { useRouter } from 'next/navigation';
import type { BuyerFormState } from '@/lib/buyer-actions';

export type FormValues = Record<string, string>;

export interface BuyerFormProps {
  action: (prev: BuyerFormState, fd: FormData) => Promise<BuyerFormState>;
  initialValues: FormValues;
  submitLabel: string;
  cancelHref: string;
}

const initialState: BuyerFormState = {};

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

export function BuyerForm({
  action,
  initialValues,
  submitLabel,
  cancelHref,
}: BuyerFormProps) {
  const [state, formAction] = useFormState(action, initialState);
  const router = useRouter();

  const v: FormValues = { ...initialValues, ...(state.values ?? {}) };
  const fe = state.fieldErrors ?? {};

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
              minLength={2}
              maxLength={200}
              className={inputCls(!!fe.name)}
            />
          </Field>
          <Field label="Country" name="country" error={fe.country}>
            <input
              type="text"
              id="country"
              name="country"
              defaultValue={v.country ?? ''}
              maxLength={80}
              placeholder="UK · IT · …"
              className={inputCls(!!fe.country)}
            />
          </Field>
          <Field label="VAT / Tax ID" name="vat" error={fe.vat}>
            <input
              type="text"
              id="vat"
              name="vat"
              defaultValue={v.vat ?? ''}
              maxLength={60}
              className={inputCls(!!fe.vat)}
            />
          </Field>
          <Field label="Contact" name="contact" error={fe.contact}>
            <input
              type="text"
              id="contact"
              name="contact"
              defaultValue={v.contact ?? ''}
              maxLength={200}
              placeholder="name · email · phone"
              className={inputCls(!!fe.contact)}
            />
          </Field>
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
