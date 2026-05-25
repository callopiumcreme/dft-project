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

export interface OceanBlHeader {
  blNo: string;
  vessel: string | null;
  voyage: string | null;
  carrier: string | null;
  blDate: string | null;
  originNode: string;
  destinationNode: string;
  kgIn: string | null;
  unitCount: number | null;
}

interface Props {
  consignmentId: number | null;
  header: OceanBlHeader | null;
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
 * Ocean BL PDF viewer popup (Cartagena → Rotterdam leg, CMA-CGM).
 * Loads the PDF via auth-gated proxy `/api/consignments/<cid>/bl/<bl_no>/pdf`
 * and renders it inline in an iframe. Download button forces attachment
 * disposition by appending `?download=1`.
 *
 * Files stored on local disk under `data/bl_ocean/c-<id>/` — no Drive runtime.
 * Filenames preserve Drive provenance (`BL_<no>_<VESSEL>_<YYYY-MM-DD>.pdf`)
 * so the audit trail from CMA-CGM → Drive → DB → server filesystem is byte-
 * identical (ISCC EU + DfT RTFO compliance).
 */
export function OceanBlModal({ consignmentId, header, onClose }: Props) {
  const isOpen = consignmentId !== null && header !== null;
  const blNo = header?.blNo ?? null;
  const pdfUrl =
    isOpen && blNo
      ? `/api/consignments/${consignmentId}/bl/${blNo}/pdf`
      : null;
  // Route segment is `[id]` (matches existing api/consignments/[id]/...) but
  // we still inject the raw numeric consignment id here.

  const handleDownload = React.useCallback(() => {
    if (!pdfUrl || !blNo) return;
    // `?download=1` flips backend Content-Disposition to attachment so
    // the browser saves instead of opening the PDF inline.
    const a = document.createElement('a');
    a.href = `${pdfUrl}?download=1`;
    a.download = `BL_${blNo}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [pdfUrl, blNo]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm tracking-[0.1em]">
            Ocean BL · {header?.blNo ?? ''}
          </DialogTitle>
          <DialogDescription className="font-mono text-[0.7rem] text-ink-mute">
            Bill of Lading — {header?.originNode ?? '—'} → {header?.destinationNode ?? '—'}.
            Cargo: DEV-P100 refined pyrolysis oil (OisteBio → UTB BV Dordrecht).
          </DialogDescription>
        </DialogHeader>

        {header && (
          <dl className="mb-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-b border-rule py-2 font-mono text-[0.7rem]">
            <DRow label="BL #" value={header.blNo} />
            <DRow label="BL date" value={fmtDate(header.blDate)} />
            <DRow label="Vessel" value={header.vessel} />
            <DRow label="Voyage" value={header.voyage} />
            <DRow label="Carrier" value={header.carrier} />
            <DRow label="Net loaded" value={fmtKg(header.kgIn)} />
            <DRow
              label="Containers"
              value={
                header.unitCount !== null ? String(header.unitCount) : null
              }
            />
            <DRow
              label="Route"
              value={`${header.originNode} → ${header.destinationNode}`}
            />
          </dl>
        )}

        {pdfUrl && (
          <iframe
            src={pdfUrl}
            title={`Ocean BL ${header?.blNo}`}
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
