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
  fetchC14CertificateMetadata,
  probeC14CertificatePdf,
  buildC14CertificatePdfUrl,
  buildC14CertificateDownloadUrl,
  C14CertificateNotFoundError,
  type C14CertificateDetail,
} from '@/lib/c14-certificate-client';

interface Props {
  c14Id: number | null;
  certNumber: string | null;
  onClose: () => void;
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; metadata: C14CertificateDetail; hasPdf: boolean }
  | { kind: 'error'; message: string; status?: number };

const monthFmt = new Intl.DateTimeFormat('en-GB', { month: 'short', year: 'numeric' });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtMonth(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return monthFmt.format(d);
}

function fmtPct(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return `${n.toFixed(2)} %`;
}

export function C14CertificateModal({ c14Id, certNumber, onClose }: Props) {
  const [state, setState] = React.useState<LoadState>({ kind: 'idle' });
  const [attempt, setAttempt] = React.useState(0);

  const isOpen = c14Id !== null;

  React.useEffect(() => {
    if (c14Id === null) {
      setState({ kind: 'idle' });
      return;
    }

    let cancelled = false;
    setState({ kind: 'loading' });

    Promise.all([
      fetchC14CertificateMetadata(c14Id),
      probeC14CertificatePdf(c14Id),
    ])
      .then(([metadata, hasPdf]) => {
        if (cancelled) return;
        setState({ kind: 'ready', metadata, hasPdf });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof C14CertificateNotFoundError) {
          setState({ kind: 'error', message: `C14 ${c14Id} not found`, status: 404 });
        } else if (err instanceof Error) {
          setState({ kind: 'error', message: err.message });
        } else {
          setState({ kind: 'error', message: 'Unknown error' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [c14Id, attempt]);

  const handleOpenChange = (next: boolean) => {
    if (!next) onClose();
  };

  const handleRetry = () => setAttempt((n) => n + 1);

  const pdfUrl = c14Id !== null ? buildC14CertificatePdfUrl(c14Id) : '#';
  const downloadUrl = c14Id !== null ? buildC14CertificateDownloadUrl(c14Id) : '#';
  const canDownload = state.kind === 'ready' && state.hasPdf;

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
        <DialogHeader className="border-b border-rule px-6 py-4">
          <DialogTitle>C14 certificate {certNumber ?? ''}</DialogTitle>
          {state.kind === 'ready' && (
            <DialogDescription className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              {state.metadata.lab && <span>{state.metadata.lab}</span>}
              <span aria-hidden="true">·</span>
              <span>{fmtMonth(state.metadata.period_month)}</span>
              <span aria-hidden="true">·</span>
              <span>{fmtPct(state.metadata.bio_carbon_pct)} bio-C</span>
              {state.metadata.method && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{state.metadata.method}</span>
                </>
              )}
              {state.metadata.deleted_at && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="bg-accent/15 text-accent px-2 py-0.5">deleted</span>
                </>
              )}
            </DialogDescription>
          )}
        </DialogHeader>

        <div className="overflow-auto bg-bg-soft min-h-[50vh]">
          {state.kind === 'ready' && (
            <p className="border-b border-rule px-6 py-3 font-mono text-[0.72rem] text-ink-soft">
              Sampled <span className="text-ink">{fmtDate(state.metadata.sampled_date)}</span>
              {' · '}Tested <span className="text-ink">{fmtDate(state.metadata.tested_date)}</span>
              {state.metadata.sample_ref && (
                <>
                  {' · '}Sample <span className="text-ink">{state.metadata.sample_ref}</span>
                </>
              )}
              {state.metadata.sustainability_decl && (
                <>
                  {' · '}SD <span className="text-ink">{state.metadata.sustainability_decl}</span>
                </>
              )}
            </p>
          )}
          {state.kind === 'loading' && (
            <div className="flex h-full min-h-[50vh] items-center justify-center">
              <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-ink-mute">
                Loading certificate…
              </p>
            </div>
          )}
          {state.kind === 'error' && (
            <div className="flex h-full min-h-[50vh] flex-col items-center justify-center gap-4 px-6 text-center">
              <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-accent">
                {state.message}
              </p>
              {state.status !== 404 && (
                <Button variant="secondary" size="sm" onClick={handleRetry}>
                  Retry
                </Button>
              )}
            </div>
          )}
          {state.kind === 'ready' && !state.hasPdf && (
            <div className="flex h-full min-h-[50vh] flex-col items-center justify-center gap-2 px-6 text-center">
              <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-ink-mute">
                Certificate PDF not available
              </p>
              <p className="font-mono text-[0.7rem] text-ink-mute">
                File: <span className="text-ink">{certNumber}.pdf</span>
              </p>
            </div>
          )}
          {state.kind === 'ready' && state.hasPdf && (
            <iframe
              title={`C14 certificate ${certNumber} preview`}
              src={`${pdfUrl}#toolbar=0&navpanes=0&view=FitH`}
              className="block h-[70vh] w-full border-0 bg-white"
            />
          )}
        </div>

        <DialogFooter className="border-t border-rule px-6 py-4">
          <Button variant="secondary" size="sm" onClick={onClose}>
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
              href={canDownload ? downloadUrl : undefined}
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
  );
}
