'use client';

import * as React from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  createSale,
  listBuyers,
  type ByproductBuyer,
  type ByproductSale,
  type ByproductSaleIn,
  type SellableKind,
  SELLABLE_KIND_LABELS,
} from '@/lib/byproduct-client';
import { BuyerForm } from './BuyerForm';

interface Props {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  initialBuyers: ByproductBuyer[];
  defaultProductKind?: SellableKind;
  onCreated?: (sale: ByproductSale) => void;
}

interface FormState {
  product_kind: SellableKind;
  buyer_id: string; // string to drive <select>; parsed at submit
  sale_date: string;
  kg_net: string;
  invoice_no: string;
  price_eur: string;
  notes: string;
}

const today = () => new Date().toISOString().slice(0, 10);

function buildInitialState(defaultProductKind?: SellableKind): FormState {
  return {
    product_kind: defaultProductKind ?? 'carbon_black',
    buyer_id: '',
    sale_date: today(),
    kg_net: '',
    invoice_no: '',
    price_eur: '',
    notes: '',
  };
}

export function SaleForm({
  open,
  onOpenChange,
  initialBuyers,
  defaultProductKind,
  onCreated,
}: Props) {
  const [form, setForm] = React.useState<FormState>(() =>
    buildInitialState(defaultProductKind),
  );
  const [buyers, setBuyers] = React.useState<ByproductBuyer[]>(initialBuyers);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [showNewBuyer, setShowNewBuyer] = React.useState(false);

  // Reset form whenever the dialog re-opens.
  React.useEffect(() => {
    if (open) {
      setForm(buildInitialState(defaultProductKind));
      setError(null);
      setShowNewBuyer(false);
      setBuyers(initialBuyers);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const update = <K extends keyof FormState>(k: K, v: FormState[K]) =>
    setForm((s) => ({ ...s, [k]: v }));

  const handleBuyerCreated = async (buyer: ByproductBuyer) => {
    // Refresh the buyer list to stay in sync with backend ordering.
    try {
      const refreshed = await listBuyers();
      setBuyers(refreshed);
    } catch {
      setBuyers((bs) => [...bs, buyer].sort((a, b) => a.name.localeCompare(b.name)));
    }
    update('buyer_id', String(buyer.id));
    setShowNewBuyer(false);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const buyerId = Number(form.buyer_id);
    if (!Number.isInteger(buyerId) || buyerId <= 0) {
      setError('Pick a buyer (or create a new one).');
      return;
    }
    const kg = Number(form.kg_net);
    if (!Number.isFinite(kg) || kg <= 0) {
      setError('kg net must be greater than 0.');
      return;
    }
    if (!form.sale_date) {
      setError('Sale date is required.');
      return;
    }
    const price = form.price_eur.trim() ? Number(form.price_eur) : undefined;
    if (price !== undefined && (!Number.isFinite(price) || price < 0)) {
      setError('Price EUR must be a non-negative number.');
      return;
    }

    const payload: ByproductSaleIn = {
      product_kind: form.product_kind,
      buyer_id: buyerId,
      sale_date: form.sale_date,
      kg_net: kg,
      invoice_no: form.invoice_no.trim() || undefined,
      price_eur: price,
      notes: form.notes.trim() || undefined,
    };

    setSubmitting(true);
    try {
      const created = await createSale(payload);
      toast.success(
        `Sale recorded: ${SELLABLE_KIND_LABELS[created.product_kind]} · ${created.kg_net} kg`,
      );
      onCreated?.(created);
      onOpenChange(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to create sale';
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>New byproduct sale</DialogTitle>
          <DialogDescription className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
            Records the invoice and posts a companion mass-balance ledger row.
          </DialogDescription>
        </DialogHeader>

        {showNewBuyer ? (
          <div className="space-y-3">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              New buyer
            </p>
            <BuyerForm
              variant="modal"
              onCreated={handleBuyerCreated}
              onCancel={() => setShowNewBuyer(false)}
            />
          </div>
        ) : (
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Product" required>
                <select
                  required
                  value={form.product_kind}
                  onChange={(e) => update('product_kind', e.target.value as SellableKind)}
                  className={inputCls}
                >
                  <option value="plus_oil">PLUS oil</option>
                  <option value="carbon_black">Carbon black</option>
                  <option value="metal_scrap">Metal scrap</option>
                </select>
              </Field>

              <Field label="Buyer" required>
                <div className="flex gap-2">
                  <select
                    required
                    value={form.buyer_id}
                    onChange={(e) => update('buyer_id', e.target.value)}
                    className={inputCls}
                  >
                    <option value="">— select —</option>
                    {buyers.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                        {b.country ? ` · ${b.country}` : ''}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setShowNewBuyer(true)}
                    className="border border-rule bg-bg-soft px-2 font-mono text-[0.7rem] uppercase tracking-[0.12em] text-ink-soft hover:border-ink hover:text-ink"
                    title="Add a new buyer"
                  >
                    + New
                  </button>
                </div>
              </Field>

              <Field label="Sale date" required>
                <input
                  type="date"
                  required
                  value={form.sale_date}
                  onChange={(e) => update('sale_date', e.target.value)}
                  className={inputCls}
                />
              </Field>

              <Field label="kg net" required>
                <input
                  type="number"
                  required
                  min={0}
                  step="0.001"
                  value={form.kg_net}
                  onChange={(e) => update('kg_net', e.target.value)}
                  className={inputCls}
                  placeholder="0.000"
                />
              </Field>

              <Field label="Invoice no.">
                <input
                  type="text"
                  maxLength={100}
                  value={form.invoice_no}
                  onChange={(e) => update('invoice_no', e.target.value)}
                  className={inputCls}
                  placeholder="INV-2026-..."
                />
              </Field>

              <Field label="Price EUR">
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.price_eur}
                  onChange={(e) => update('price_eur', e.target.value)}
                  className={inputCls}
                  placeholder="0.00"
                />
              </Field>
            </div>

            <Field label="Notes">
              <textarea
                rows={2}
                maxLength={2000}
                value={form.notes}
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

            <div className="flex items-center gap-3 border-t border-rule pt-4">
              <button
                type="submit"
                disabled={submitting}
                className="border border-ink bg-ink px-5 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? 'Saving…' : 'Record sale'}
              </button>
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="border border-rule bg-bg-soft px-5 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink-soft hover:border-ink hover:text-ink"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
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
