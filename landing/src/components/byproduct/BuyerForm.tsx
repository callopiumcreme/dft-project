'use client';

import * as React from 'react';
import { toast } from 'sonner';
import {
  createBuyer,
  type ByproductBuyer,
  type ByproductBuyerIn,
} from '@/lib/byproduct-client';

interface Props {
  /** Called with the freshly-created buyer on success. */
  onCreated?: (buyer: ByproductBuyer) => void;
  /** Optional close handler when used inside a dialog. */
  onCancel?: () => void;
  /** Compact (modal) layout vs. full (inline page) layout. */
  variant?: 'inline' | 'modal';
}

const emptyForm: ByproductBuyerIn = {
  name: '',
  country: '',
  vat: '',
  contact: '',
  notes: '',
};

export function BuyerForm({ onCreated, onCancel, variant = 'inline' }: Props) {
  const [form, setForm] = React.useState<ByproductBuyerIn>(emptyForm);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const update = <K extends keyof ByproductBuyerIn>(k: K, v: ByproductBuyerIn[K]) =>
    setForm((s) => ({ ...s, [k]: v }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const name = (form.name ?? '').trim();
    if (name.length < 2) {
      setError('Name must be at least 2 characters.');
      return;
    }

    setSubmitting(true);
    try {
      const payload: ByproductBuyerIn = {
        name,
        country: form.country?.trim() || undefined,
        vat: form.vat?.trim() || undefined,
        contact: form.contact?.trim() || undefined,
        notes: form.notes?.trim() || undefined,
      };
      const created = await createBuyer(payload);
      toast.success(`Buyer "${created.name}" created`);
      setForm(emptyForm);
      onCreated?.(created);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to create buyer';
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      <div className={variant === 'modal' ? 'space-y-3' : 'grid grid-cols-1 sm:grid-cols-2 gap-4'}>
        <Field label="Name" required>
          <input
            type="text"
            required
            minLength={2}
            maxLength={200}
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            className={inputCls}
            placeholder="Recycling Co. SAS"
          />
        </Field>
        <Field label="Country">
          <input
            type="text"
            maxLength={100}
            value={form.country ?? ''}
            onChange={(e) => update('country', e.target.value)}
            className={inputCls}
            placeholder="CO"
          />
        </Field>
        <Field label="VAT / NIT">
          <input
            type="text"
            maxLength={50}
            value={form.vat ?? ''}
            onChange={(e) => update('vat', e.target.value)}
            className={inputCls}
            placeholder="900.123.456-7"
          />
        </Field>
        <Field label="Contact">
          <input
            type="text"
            maxLength={200}
            value={form.contact ?? ''}
            onChange={(e) => update('contact', e.target.value)}
            className={inputCls}
            placeholder="ops@buyer.com / +57 ..."
          />
        </Field>
      </div>

      <Field label="Notes">
        <textarea
          rows={2}
          maxLength={2000}
          value={form.notes ?? ''}
          onChange={(e) => update('notes', e.target.value)}
          className={`${inputCls} resize-y`}
        />
      </Field>

      {error && (
        <p
          role="alert"
          className="border border-accent bg-accent/5 px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-accent"
        >
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={submitting}
          className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? 'Saving…' : 'Add buyer'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="border border-rule bg-bg-soft px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft hover:border-ink hover:text-ink"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

const inputCls =
  'w-full border border-rule bg-bg-soft px-2 py-1.5 font-mono text-[0.78rem] text-ink focus:outline-none focus:border-ink';

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
        {label}
        {required && <span className="ml-1 text-accent">*</span>}
      </span>
      {children}
    </label>
  );
}
