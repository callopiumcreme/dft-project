'use client';

import { useFormState, useFormStatus } from 'react-dom';
import type { CertificateFormState } from '@/lib/certificate-actions';
import type { components } from '@/lib/backend-types';

type Supplier = components['schemas']['SupplierRead'];
type Certificate = components['schemas']['CertificateRead'];
type Status = 'active' | 'expired' | 'revoked' | 'placeholder';

const STATUSES: Status[] = ['active', 'expired', 'revoked', 'placeholder'];
const STATUS_LABEL: Record<Status, string> = {
  active: 'Active',
  expired: 'Expired',
  revoked: 'Revoked',
  placeholder: 'Placeholder',
};

type Action = (
  prev: CertificateFormState,
  fd: FormData,
) => Promise<CertificateFormState>;

interface Props {
  action: Action;
  suppliers: Supplier[];
  initial?: Certificate | null;
  submitLabel: string;
  cancelHref: string;
}

const initialState: CertificateFormState = {};

function ErrorMsg({ msg }: { msg?: string }) {
  if (!msg) return null;
  return (
    <p className="mt-1 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-accent">
      {msg}
    </p>
  );
}

function FieldLabel({
  htmlFor,
  required,
  children,
}: {
  htmlFor: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute"
    >
      {children}
      {required && <span className="ml-1 text-accent">*</span>}
    </label>
  );
}

function Submit({ label }: { label: string }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft disabled:opacity-50"
    >
      {pending ? 'Saving…' : label}
    </button>
  );
}

export default function CertificateForm({
  action,
  suppliers,
  initial,
  submitLabel,
  cancelHref,
}: Props) {
  const [state, formAction] = useFormState(action, initialState);
  const v = state.values ?? {};
  const errs = state.fieldErrors ?? {};

  const initialSupplierIds = new Set<number>(
    state.supplierIds ?? initial?.supplier_ids ?? [],
  );

  const value = (k: string, fallback?: string | null): string => {
    if (v[k] !== undefined) return v[k];
    if (fallback === null || fallback === undefined) return '';
    return String(fallback);
  };

  const checked = (k: string, fallback?: boolean): boolean => {
    if (v[k] !== undefined)
      return v[k] === 'on' || v[k] === 'true' || v[k] === '1';
    return !!fallback;
  };

  return (
    <form action={formAction} className="mt-8 space-y-8 font-mono text-[0.78rem]">
      {state.error && (
        <p
          role="alert"
          className="border border-accent bg-accent/5 px-3 py-2 text-[0.7rem] uppercase tracking-[0.14em] text-accent"
        >
          {state.error}
        </p>
      )}

      <fieldset className="space-y-4 border border-rule bg-bg-soft p-4">
        <legend className="px-2 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Identity
        </legend>

        <div>
          <FieldLabel htmlFor="cert_number" required>
            Certificate number
          </FieldLabel>
          <input
            id="cert_number"
            name="cert_number"
            required
            maxLength={64}
            defaultValue={value('cert_number', initial?.cert_number)}
            className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
            aria-invalid={!!errs.cert_number}
          />
          <ErrorMsg msg={errs.cert_number} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="scheme">Scheme</FieldLabel>
            <input
              id="scheme"
              name="scheme"
              maxLength={64}
              defaultValue={value('scheme', initial?.scheme ?? 'ISCC EU')}
              className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
              aria-invalid={!!errs.scheme}
            />
            <ErrorMsg msg={errs.scheme} />
          </div>
          <div>
            <FieldLabel htmlFor="status">Status</FieldLabel>
            <select
              id="status"
              name="status"
              defaultValue={value('status', initial?.status ?? 'active')}
              className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
              aria-invalid={!!errs.status}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
            <ErrorMsg msg={errs.status} />
          </div>
        </div>
      </fieldset>

      <fieldset className="space-y-4 border border-rule bg-bg-soft p-4">
        <legend className="px-2 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Validity
        </legend>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <FieldLabel htmlFor="issued_at">Issued at</FieldLabel>
            <input
              id="issued_at"
              name="issued_at"
              type="date"
              defaultValue={value('issued_at', initial?.issued_at)}
              className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
              aria-invalid={!!errs.issued_at}
            />
            <ErrorMsg msg={errs.issued_at} />
          </div>
          <div>
            <FieldLabel htmlFor="expires_at">Expires at</FieldLabel>
            <input
              id="expires_at"
              name="expires_at"
              type="date"
              defaultValue={value('expires_at', initial?.expires_at)}
              className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
              aria-invalid={!!errs.expires_at}
            />
            <ErrorMsg msg={errs.expires_at} />
          </div>
        </div>

        <label className="flex items-center gap-2 text-[0.72rem] text-ink-soft">
          <input
            type="checkbox"
            name="is_placeholder"
            defaultChecked={checked('is_placeholder', initial?.is_placeholder)}
          />
          Placeholder certificate (not yet uploaded)
        </label>
      </fieldset>

      <fieldset className="space-y-4 border border-rule bg-bg-soft p-4">
        <legend className="px-2 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Suppliers covered
        </legend>
        <p className="text-[0.7rem] text-ink-mute">
          Select all suppliers covered by this certificate. Hold Ctrl/Cmd to multi-select.
        </p>
        <select
          name="supplier_ids"
          multiple
          size={Math.min(8, Math.max(4, suppliers.length))}
          defaultValue={Array.from(initialSupplierIds, String)}
          className="w-full border border-rule bg-bg px-2 py-1.5 text-ink"
        >
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.code} · {s.name}
            </option>
          ))}
        </select>
      </fieldset>

      <fieldset className="space-y-4 border border-rule bg-bg-soft p-4">
        <legend className="px-2 font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
          Document & notes
        </legend>
        <div>
          <FieldLabel htmlFor="document_url">Document URL</FieldLabel>
          <input
            id="document_url"
            name="document_url"
            type="url"
            maxLength={1000}
            defaultValue={value('document_url', initial?.document_url)}
            placeholder="https://…"
            className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
            aria-invalid={!!errs.document_url}
          />
          <ErrorMsg msg={errs.document_url} />
        </div>
        <div>
          <FieldLabel htmlFor="notes">Notes</FieldLabel>
          <textarea
            id="notes"
            name="notes"
            rows={4}
            maxLength={4000}
            defaultValue={value('notes', initial?.notes)}
            className="mt-1 w-full border border-rule bg-bg px-2 py-1.5 text-ink"
            aria-invalid={!!errs.notes}
          />
          <ErrorMsg msg={errs.notes} />
        </div>
      </fieldset>

      <div className="flex items-center gap-3">
        <Submit label={submitLabel} />
        <a
          href={cancelHref}
          className="border border-rule px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft hover:border-ink hover:text-ink"
        >
          Cancel
        </a>
      </div>
    </form>
  );
}
