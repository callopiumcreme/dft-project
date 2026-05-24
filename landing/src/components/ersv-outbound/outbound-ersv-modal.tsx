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
  fetchOutboundErsvHtml,
  buildOutboundErsvPdfUrl,
  ErsvOutboundNotFoundError,
} from '@/lib/ersv-outbound-client';

export interface OutboundErsvHeader {
  offTakerCode?: string | null;
  posNumber: string;
  kgNet?: string | null;
  ersvOutboundNo?: string | null;
  prodDateFrom?: string | null;
  prodDateTo?: string | null;
}

interface Props {
  consignmentId: number | null;
  posNumber: string | null;
  header: OutboundErsvHeader | null;
  onClose: () => void;
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; html: string }
  | { kind: 'error'; message: string; status?: number };

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return numFmt.format(n);
}

function fmtRange(from?: string | null, to?: string | null): string | null {
  if (!from && !to) return null;
  if (from && to && from !== to) return `${from} → ${to}`;
  return from ?? to ?? null;
}

export function OutboundErsvModal({ consignmentId, posNumber, header, onClose }: Props) {
  const [state, setState] = React.useState<LoadState>({ kind: 'idle' });
  const [attempt, setAttempt] = React.useState(0);

  const isOpen = consignmentId !== null && posNumber !== null && header !== null;

  React.useEffect(() => {
    if (consignmentId === null || posNumber === null) {
      setState({ kind: 'idle' });
      return;
    }

    let cancelled = false;
    setState({ kind: 'loading' });

    fetchOutboundErsvHtml(consignmentId, posNumber)
      .then((htmlRes) => {
        if (cancelled) return;
        setState({ kind: 'ready', html: htmlRes.html });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ErsvOutboundNotFoundError) {
          setState({
            kind: 'error',
            message: `Outbound eRSV ${consignmentId}/${posNumber} not found`,
            status: 404,
          });
        } else if (err instanceof Error) {
          setState({ kind: 'error', message: err.message });
        } else {
          setState({ kind: 'error', message: 'Unknown error' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [consignmentId, posNumber, attempt]);

  const handleOpenChange = (next: boolean) => {
    if (!next) onClose();
  };

  const handleRetry = () => setAttempt((n) => n + 1);

  const pdfUrl =
    consignmentId !== null && posNumber !== null
      ? buildOutboundErsvPdfUrl(consignmentId, posNumber)
      : '#';

  const prodRange = header ? fmtRange(header.prodDateFrom, header.prodDateTo) : null;

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
        <DialogHeader className="border-b border-rule px-6 py-4">
          <DialogTitle>eRSV outbound — {posNumber ?? ''}</DialogTitle>
          {header && (
            <DialogDescription className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              {header.offTakerCode && (
                <>
                  <span>{header.offTakerCode}</span>
                  <span aria-hidden="true">·</span>
                </>
              )}
              {prodRange && (
                <>
                  <span>{prodRange}</span>
                  <span aria-hidden="true">·</span>
                </>
              )}
              <span>{fmtKg(header.kgNet)} kg</span>
              {header.ersvOutboundNo && (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{header.ersvOutboundNo}</span>
                </>
              )}
            </DialogDescription>
          )}
        </DialogHeader>

        <div className="overflow-auto bg-bg-soft min-h-[50vh]">
          {state.kind === 'loading' && (
            <div className="flex h-full min-h-[50vh] items-center justify-center">
              <p className="font-mono text-[0.75rem] uppercase tracking-[0.14em] text-ink-mute">
                Loading eRSV…
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
          {state.kind === 'ready' && (
            <iframe
              title={`Outbound eRSV ${posNumber ?? ''} preview`}
              sandbox="allow-same-origin"
              srcDoc={state.html}
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
            disabled={state.kind !== 'ready'}
            aria-disabled={state.kind !== 'ready'}
          >
            <a
              href={state.kind === 'ready' ? pdfUrl : undefined}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => {
                if (state.kind !== 'ready') e.preventDefault();
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
