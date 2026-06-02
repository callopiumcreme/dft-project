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

interface Props {
  certId: number;
  certNumber: string;
  /** Stored pdf_ref (relative path on disk); shown when the file is missing. */
  pdfRef: string | null;
}

type Probe =
  | { kind: 'idle' }
  | { kind: 'probing' }
  | { kind: 'ready' }
  | { kind: 'missing'; status?: number };

function buildPdfUrl(certId: number): string {
  return `/api/certificates/${certId}/pdf`;
}

function buildDownloadUrl(certId: number): string {
  return `/api/certificates/${certId}/pdf/download`;
}

export function CertPdfViewer({ certId, certNumber, pdfRef }: Props) {
  const [open, setOpen] = React.useState(false);
  const [probe, setProbe] = React.useState<Probe>({ kind: 'idle' });

  React.useEffect(() => {
    if (!open) {
      setProbe({ kind: 'idle' });
      return;
    }
    let cancelled = false;
    setProbe({ kind: 'probing' });
    fetch(buildPdfUrl(certId), {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Range: 'bytes=0-0' },
    })
      .then((res) => {
        if (cancelled) return;
        if (res.ok || res.status === 206) setProbe({ kind: 'ready' });
        else setProbe({ kind: 'missing', status: res.status });
      })
      .catch(() => {
        if (!cancelled) setProbe({ kind: 'missing' });
      });
    return () => {
      cancelled = true;
    };
  }, [open, certId]);

  const canDownload = probe.kind === 'ready';

  return (
    <>
      <Button variant="primary" size="sm" onClick={() => setOpen(true)}>
        View PDF
      </Button>

      <Dialog open={open} onOpenChange={(next) => !next && setOpen(false)}>
        <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
          <DialogHeader className="border-b border-rule px-6 py-4">
            <DialogTitle>{certNumber}</DialogTitle>
            <DialogDescription className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute break-all">
              {pdfRef ?? 'no pdf_ref'}
            </DialogDescription>
          </DialogHeader>

          <div className="overflow-auto bg-bg-soft min-h-[50vh]">
            {probe.kind === 'probing' && (
              <div className="flex h-full min-h-[50vh] items-center justify-center">
                <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-ink-mute">
                  Loading PDF…
                </p>
              </div>
            )}
            {probe.kind === 'missing' && (
              <div className="flex h-full min-h-[50vh] flex-col items-center justify-center gap-2 px-6 text-center">
                <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-accent">
                  PDF not available
                </p>
                <p className="font-mono text-[0.7rem] text-ink-mute break-all">
                  {pdfRef ? <span className="text-ink">{pdfRef}</span> : 'No pdf_ref set on this certificate'}
                </p>
              </div>
            )}
            {probe.kind === 'ready' && (
              <iframe
                title={`${certNumber} preview`}
                src={buildPdfUrl(certId)}
                className="block h-[70vh] w-full border-0 bg-white"
              />
            )}
          </div>

          <DialogFooter className="border-t border-rule px-6 py-4">
            <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
              Close
            </Button>
            <Button
              variant="primary"
              size="sm"
              asChild
              disabled={!canDownload}
              aria-disabled={!canDownload}
            >
              <a
                href={canDownload ? buildDownloadUrl(certId) : undefined}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => {
                  if (!canDownload) e.preventDefault();
                }}
              >
                Download PDF
              </a>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
