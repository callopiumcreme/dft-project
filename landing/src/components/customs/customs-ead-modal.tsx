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

export interface CustomsEadHeader {
  posNumber: string;
  mrn: string;
  lrn: string | null;
  customsOffice: string | null;
  containerNo: string | null;
  netKg: string | null;
  grossKg: string | null;
  invoiceNo: string | null;
  declarantName: string | null;
  declarantVat: string | null;
  issuingDate: string | null;
}

interface Props {
  consignmentId: number | null;
  header: CustomsEadHeader | null;
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
 * EAD (DMS Export) PDF viewer popup.
 * Loads the PDF via auth-gated proxy `/api/customs/<cid>/<mrn>/pdf` and renders
 * it inline in an iframe. Download button forces attachment disposition by
 * appending `?download=1` — handled client-side via a hidden link.
 *
 * Files stored on local disk under `data/customs/c-<id>/` — no Drive runtime.
 */
export function CustomsEadModal({ consignmentId, header, onClose }: Props) {
  const isOpen = consignmentId !== null && header !== null;
  const mrn = header?.mrn ?? null;
  const pdfUrl = isOpen && mrn ? `/api/customs/${consignmentId}/${mrn}/pdf` : null;

  const handleDownload = React.useCallback(() => {
    if (!pdfUrl) return;
    // `?download=1` flips backend Content-Disposition to attachment so
    // the browser saves instead of opening the PDF inline.
    const a = document.createElement('a');
    a.href = `${pdfUrl}?download=1`;
    a.download = `DMS_EXPORT_${mrn}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [pdfUrl, mrn]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm tracking-[0.1em]">
            EAD · {header?.mrn ?? ''}
          </DialogTitle>
          <DialogDescription className="font-mono text-[0.7rem] text-ink-mute">
            DMS Export Accompanying Document — filed by{' '}
            {header?.declarantName ?? 'BiNova BV'}
            {header?.declarantVat ? ` (${header.declarantVat})` : ''} as NL customs
            declarant for OisteBio Swiss GmbH.
          </DialogDescription>
        </DialogHeader>

        {header && (
          <dl className="mb-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-b border-rule py-2 font-mono text-[0.7rem]">
            <DRow label="PoS" value={header.posNumber} />
            <DRow label="LRN" value={header.lrn} />
            <DRow label="Container" value={header.containerNo} />
            <DRow label="Customs office" value={header.customsOffice} />
            <DRow label="Net" value={fmtKg(header.netKg)} />
            <DRow label="Gross" value={fmtKg(header.grossKg)} />
            <DRow label="Invoice" value={header.invoiceNo} />
            <DRow label="Issuing date" value={fmtDate(header.issuingDate)} />
          </dl>
        )}

        {pdfUrl && (
          <iframe
            src={pdfUrl}
            title={`EAD ${header?.mrn}`}
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
