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
  fetchProductPurchaseMetadata,
  probeProductPurchasePdf,
  buildProductPurchasePdfUrl,
  buildProductPurchaseDownloadUrl,
  ProductPurchaseNotFoundError,
  type ProductPurchaseDetail,
} from '@/lib/product-purchase-client';

interface Props {
  ppId: number | null;
  posNumber: string | null;
  onClose: () => void;
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; metadata: ProductPurchaseDetail; hasPdf: boolean }
  | { kind: 'error'; message: string; status?: number };

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 3 });
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
  return `${numFmt.format(n)} kg`;
}

export function ProductPurchaseModal({ ppId, posNumber, onClose }: Props) {
  const [state, setState] = React.useState<LoadState>({ kind: 'idle' });
  const [attempt, setAttempt] = React.useState(0);

  const isOpen = ppId !== null;

  React.useEffect(() => {
    if (ppId === null) {
      setState({ kind: 'idle' });
      return;
    }

    let cancelled = false;
    setState({ kind: 'loading' });

    Promise.all([
      fetchProductPurchaseMetadata(ppId),
      probeProductPurchasePdf(ppId),
    ])
      .then(([metadata, hasPdf]) => {
        if (cancelled) return;
        setState({ kind: 'ready', metadata, hasPdf });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ProductPurchaseNotFoundError) {
          setState({ kind: 'error', message: `PoS ${ppId} not found`, status: 404 });
        } else if (err instanceof Error) {
          setState({ kind: 'error', message: err.message });
        } else {
          setState({ kind: 'error', message: 'Unknown error' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ppId, attempt]);

  const handleOpenChange = (next: boolean) => {
    if (!next) onClose();
  };

  const handleRetry = () => setAttempt((n) => n + 1);

  const pdfUrl = ppId !== null ? buildProductPurchasePdfUrl(ppId) : '#';
  const downloadUrl = ppId !== null ? buildProductPurchaseDownloadUrl(ppId) : '#';
  const canDownload = state.kind === 'ready' && state.hasPdf;

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
        <DialogHeader className="border-b border-rule px-6 py-4">
          <DialogTitle>PoS {posNumber ?? ''}</DialogTitle>
          {state.kind === 'ready' && (
            <DialogDescription className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              {state.metadata.supplier_name && (
                <span>{state.metadata.supplier_name}</span>
              )}
              <span aria-hidden="true">·</span>
              <span>{fmtDate(state.metadata.issuance_date)}</span>
              <span aria-hidden="true">·</span>
              <span>{fmtKg(state.metadata.quantity_kg)}</span>
              {state.metadata.feedstock && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{state.metadata.feedstock}</span>
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
          {state.kind === 'ready' && state.metadata.dispatch_label && (
            <p className="border-b border-rule px-6 py-3 font-mono text-[0.72rem] text-ink-soft">
              Dispatch: <span className="text-ink">{state.metadata.dispatch_label}</span>
            </p>
          )}
          {state.kind === 'loading' && (
            <div className="flex h-full min-h-[50vh] items-center justify-center">
              <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-ink-mute">
                Loading PoS…
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
                PoS PDF not available
              </p>
              <p className="font-mono text-[0.7rem] text-ink-mute">
                File: <span className="text-ink">{posNumber}.pdf</span>
              </p>
            </div>
          )}
          {state.kind === 'ready' && state.hasPdf && (
            <iframe
              title={`PoS ${posNumber} preview`}
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
                if (!canDownload) {
                  e.preventDefault();
                  return;
                }
                window.trackEvent?.('doc_pdf_download', {
                  entity: 'product_purchase',
                  id: ppId,
                });
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
