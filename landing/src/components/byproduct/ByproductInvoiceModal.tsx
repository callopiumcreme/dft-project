'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  SELLABLE_KIND_LABELS,
  type ByproductSale,
} from '@/lib/byproduct-client';

type ModalVariant = 'invoice' | 'pos';

interface Props {
  sale: ByproductSale | null;
  onClose: () => void;
  /** Which document the modal previews. Defaults to 'invoice'. */
  variant?: ModalVariant;
}

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 3 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${numFmt.format(n)} kg`;
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtMoney(amount: string | null | undefined, currency: string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') return '—';
  const n = Number(amount);
  if (!Number.isFinite(n)) return '—';
  const c = (currency ?? 'EUR').toUpperCase();
  const f = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  return `${f.format(n)} ${c}`;
}

/**
 * Byproduct-sale invoice PDF viewer popup.
 *
 * Loads the per-sale PDF via auth-gated proxy `/api/byproduct/sales/<id>/pdf`
 * and renders it inline in an iframe. Download button forces attachment
 * disposition via `?download=1` query.
 *
 * Files stored on local disk under `data/byproduct/c-<sale_id>.pdf` —
 * no Drive runtime. Mirrors the CustomsEadModal pattern.
 */
export function ByproductInvoiceModal({ sale, onClose, variant = 'invoice' }: Props) {
  const isOpen = sale !== null;
  const isPos = variant === 'pos';
  const pdfUrl = isOpen && sale?.id
    ? (isPos
        ? `/api/byproduct/sales/${sale.id}/pos`
        : `/api/byproduct/sales/${sale.id}/pdf`)
    : null;
  const filename = isPos
    ? `${sale?.pos_no ?? 'pos'}.pdf`
    : (sale?.invoice_no ? `${sale.invoice_no}.pdf` : 'invoice.pdf');

  const handleDownload = React.useCallback(() => {
    if (!pdfUrl) return;
    const a = document.createElement('a');
    a.href = `${pdfUrl}?download=1`;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [pdfUrl, filename]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm tracking-[0.1em]">
            {isPos ? 'POS' : 'Invoice'} · {isPos ? (sale?.pos_no ?? '—') : (sale?.invoice_no ?? '—')}
          </DialogTitle>
          <DialogDescription className="font-mono text-[0.7rem] text-ink-mute">
            {isPos
              ? `Proof of Sustainability — OisteBio GmbH to ${sale?.buyer_name ?? '—'}.`
              : `Commercial invoice — OisteBio GmbH to ${sale?.buyer_name ?? '—'}.`}
          </DialogDescription>
        </DialogHeader>

        {sale && (
          <dl className="mb-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-b border-rule py-2 font-mono text-[0.7rem]">
            <DRow label="Product" value={SELLABLE_KIND_LABELS[sale.product_kind]} />
            <DRow label="Sale date" value={fmtDate(sale.sale_date)} />
            <DRow label="Buyer" value={sale.buyer_name ?? `#${sale.buyer_id}`} />
            <DRow label="Net" value={fmtKg(sale.kg_net)} />
            <DRow label="Amount" value={fmtMoney(sale.price_amount, sale.currency)} />
            <DRow label="Pricing" value={sale.pricing_method ?? '—'} />
          </dl>
        )}

        {pdfUrl && (
          <iframe
            src={pdfUrl}
            title={
              isPos
                ? `POS ${sale?.pos_no ?? ''}`
                : `Invoice ${sale?.invoice_no ?? ''}`
            }
            className="h-[60vh] w-full border border-rule"
          />
        )}

        <DialogFooter>
          <Button variant="secondary" onClick={handleDownload} disabled={!pdfUrl}>
            Download PDF
          </Button>
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <>
      <dt className="text-ink-mute uppercase tracking-[0.1em]">{label}</dt>
      <dd className="text-ink tabular-nums">
        {value ?? <span className="text-ink-mute">—</span>}
      </dd>
    </>
  );
}
