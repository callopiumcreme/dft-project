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
  fetchContractMetadata,
  probeContractPdf,
  buildContractPdfUrl,
  buildContractDownloadUrl,
  ContractNotFoundError,
  type ContractDetail,
} from '@/lib/contract-client';

interface Props {
  contractId: number | null;
  contractCode: string | null;
  onClose: () => void;
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; metadata: ContractDetail; hasPdf: boolean }
  | { kind: 'error'; message: string; status?: number };

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return numFmt.format(n);
}

export function ContractModal({ contractId, contractCode, onClose }: Props) {
  const [state, setState] = React.useState<LoadState>({ kind: 'idle' });
  const [attempt, setAttempt] = React.useState(0);

  const isOpen = contractId !== null;

  React.useEffect(() => {
    if (contractId === null) {
      setState({ kind: 'idle' });
      return;
    }

    let cancelled = false;
    setState({ kind: 'loading' });

    Promise.all([
      fetchContractMetadata(contractId),
      probeContractPdf(contractId),
    ])
      .then(([metadata, hasPdf]) => {
        if (cancelled) return;
        setState({ kind: 'ready', metadata, hasPdf });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ContractNotFoundError) {
          setState({ kind: 'error', message: `Contract ${contractId} not found`, status: 404 });
        } else if (err instanceof Error) {
          setState({ kind: 'error', message: err.message });
        } else {
          setState({ kind: 'error', message: 'Unknown error' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [contractId, attempt]);

  const handleOpenChange = (next: boolean) => {
    if (!next) onClose();
  };

  const handleRetry = () => setAttempt((n) => n + 1);

  const pdfUrl = contractId !== null ? buildContractPdfUrl(contractId) : '#';
  const downloadUrl = contractId !== null ? buildContractDownloadUrl(contractId) : '#';
  const canDownload = state.kind === 'ready' && state.hasPdf;

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
        <DialogHeader className="border-b border-rule px-6 py-4">
          <DialogTitle>Contract {contractCode ?? ''}</DialogTitle>
          {state.kind === 'ready' && (
            <DialogDescription className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              <span>
                {fmtDate(state.metadata.start_date)} → {fmtDate(state.metadata.end_date)}
              </span>
              <span aria-hidden="true">·</span>
              <span>{fmtKg(state.metadata.total_kg_committed)} kg</span>
              {state.metadata.is_placeholder && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="bg-accent/15 text-accent px-2 py-0.5">placeholder</span>
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
          {state.kind === 'loading' && (
            <div className="flex h-full min-h-[50vh] items-center justify-center">
              <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-ink-mute">
                Loading contract…
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
                Signed PDF not available
              </p>
              <p className="font-mono text-[0.7rem] text-ink-mute">
                Code: <span className="text-ink">{contractCode}.pdf</span>
              </p>
            </div>
          )}
          {state.kind === 'ready' && state.hasPdf && (
            <iframe
              title={`Contract ${contractCode} preview`}
              src={pdfUrl}
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
