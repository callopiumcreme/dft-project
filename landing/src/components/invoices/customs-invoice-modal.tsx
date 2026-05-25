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

export interface CustomsInvoiceHeader {
  posNumber: string;
  invoiceNo: string;
  mrn: string | null;
  netKg: string | null;
  issuingDate: string | null;
}

interface Props {
  consignmentId: number | null;
  header: CustomsInvoiceHeader | null;
  onClose: () => void;
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

/**
 * Commercial invoice PDF viewer popup (OisteBio → Crown Oil Ltd).
 * Loads the PDF via auth-gated proxy `/api/invoices/<cid>/<inv>/pdf` and
 * renders it inline in an iframe. Download button forces attachment
 * disposition by appending `?download=1`.
 *
 * Files stored on local disk under `data/invoices/c-<id>/` — no Drive runtime.
 * 1:1 mapping with the EAD PoS row (see backfill_consignment_pos_invoices).
 */
export function CustomsInvoiceModal({ consignmentId, header, onClose }: Props) {
  const isOpen = consignmentId !== null && header !== null;
  const invoiceNo = header?.invoiceNo ?? null;
  const pdfUrl =
    isOpen && invoiceNo
      ? `/api/invoices/${consignmentId}/${invoiceNo}/pdf`
      : null;

  const handleDownload = React.useCallback(() => {
    if (!pdfUrl || !invoiceNo) return;
    // `?download=1` flips backend Content-Disposition to attachment so
    // the browser saves instead of opening the PDF inline.
    const a = document.createElement('a');
    a.href = `${pdfUrl}?download=1`;
    a.download = `INV_${invoiceNo}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [pdfUrl, invoiceNo]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm tracking-[0.1em]">
            Invoice · {header?.invoiceNo ?? ''}
          </DialogTitle>
          <DialogDescription className="font-mono text-[0.7rem] text-ink-mute">
            Commercial invoice — OisteBio Swiss GmbH to Crown Oil Ltd (UK).
            Pairs 1:1 with the EAD (MRN {header?.mrn ?? '—'}) on this PoS.
          </DialogDescription>
        </DialogHeader>

        {header && (
          <dl className="mb-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-b border-rule py-2 font-mono text-[0.7rem]">
            <DRow label="PoS" value={header.posNumber} />
            <DRow label="Invoice #" value={header.invoiceNo} />
            <DRow label="MRN (EAD)" value={header.mrn} />
            <DRow label="Net" value={fmtKg(header.netKg)} />
            <DRow label="Issuing date" value={fmtDate(header.issuingDate)} />
          </dl>
        )}

        {pdfUrl && (
          <iframe
            src={pdfUrl}
            title={`Invoice ${header?.invoiceNo}`}
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
