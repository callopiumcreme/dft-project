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

export interface CertificatePdfHeader {
  certNumber: string;
  scheme: string;
  status: string;
  issuedAt: string | null;
  expiresAt: string | null;
  isPlaceholder?: boolean;
}

interface Props {
  certId: number | null;
  header: CertificatePdfHeader | null;
  onClose: () => void;
}

const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

/**
 * ISCC certificate PDF viewer popup (DFTEN-178 / E8-F5).
 *
 * Loads the PDF via auth-gated proxy `/api/certificates/<id>/pdf` and
 * renders it inline in an iframe. Download button forces attachment
 * disposition by appending `?download=1`.
 *
 * Files stored on local disk under `data/certificates/` — no Drive
 * runtime. The scheme registry (ISCC EU, RTFO accreditation, etc.) is
 * the source of truth for the cert_number; we only display the local
 * archive copy.
 */
export function CertificatePdfModal({ certId, header, onClose }: Props) {
  const isOpen = certId !== null && header !== null;
  const pdfUrl = isOpen ? `/api/certificates/${certId}/pdf` : null;

  const handleDownload = React.useCallback(() => {
    if (!pdfUrl || !header) return;
    // `?download=1` flips backend Content-Disposition to attachment.
    const safeNo = header.certNumber.replace(/[^A-Za-z0-9_.-]+/g, '_');
    const a = document.createElement('a');
    a.href = `${pdfUrl}?download=1`;
    a.download = `${safeNo}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [pdfUrl, header]);

  return (
    <Dialog open={isOpen} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm tracking-[0.1em]">
            Certificate · {header?.certNumber ?? ''}
          </DialogTitle>
          <DialogDescription className="font-mono text-[0.7rem] text-ink-mute">
            {header?.scheme ?? '—'} sustainability certificate.
            {header?.isPlaceholder ? ' (placeholder — no upstream issuer.)' : ''}
          </DialogDescription>
        </DialogHeader>

        {header && (
          <dl className="mb-3 grid grid-cols-2 gap-x-4 gap-y-1 border-t border-b border-rule py-2 font-mono text-[0.7rem]">
            <DRow label="Cert #" value={header.certNumber} />
            <DRow label="Scheme" value={header.scheme} />
            <DRow label="Status" value={header.status} />
            <DRow
              label="Type"
              value={header.isPlaceholder ? 'placeholder' : 'real'}
            />
            <DRow label="Issued" value={fmtDate(header.issuedAt)} />
            <DRow label="Expires" value={fmtDate(header.expiresAt)} />
          </dl>
        )}

        {pdfUrl && (
          <iframe
            src={pdfUrl}
            title={`Certificate ${header?.certNumber}`}
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
