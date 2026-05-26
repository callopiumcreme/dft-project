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
  fetchErsvHtml,
  fetchErsvMetadata,
  buildErsvPdfUrl,
  ErsvNotFoundError,
  type ErsvDetail,
} from '@/lib/ersv-client';
import { SyntheticRenderBanner } from '@/components/audit/synthetic-render-banner';

interface Props {
  ersvNumber: string | null;
  dailyInputId?: number | null;
  onClose: () => void;
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; metadata: ErsvDetail; html: string }
  | { kind: 'error'; message: string; status?: number };

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return numFmt.format(n);
}

export function ErsvModal({ ersvNumber, dailyInputId = null, onClose }: Props) {
  const [state, setState] = React.useState<LoadState>({ kind: 'idle' });
  const [attempt, setAttempt] = React.useState(0);

  const isOpen = ersvNumber !== null;

  React.useEffect(() => {
    if (!ersvNumber) {
      setState({ kind: 'idle' });
      return;
    }

    let cancelled = false;
    setState({ kind: 'loading' });

    Promise.all([
      fetchErsvMetadata(ersvNumber, dailyInputId),
      fetchErsvHtml(ersvNumber, dailyInputId),
    ])
      .then(([metadata, htmlRes]) => {
        if (cancelled) return;
        setState({ kind: 'ready', metadata, html: htmlRes.html });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ErsvNotFoundError) {
          setState({ kind: 'error', message: `eRSV ${ersvNumber} not found`, status: 404 });
        } else if (err instanceof Error) {
          setState({ kind: 'error', message: err.message });
        } else {
          setState({ kind: 'error', message: 'Unknown error' });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ersvNumber, dailyInputId, attempt]);

  const handleOpenChange = (next: boolean) => {
    if (!next) onClose();
  };

  const handleRetry = () => setAttempt((n) => n + 1);

  const pdfUrl = ersvNumber ? buildErsvPdfUrl(ersvNumber, dailyInputId) : '#';

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
        <DialogHeader className="border-b border-rule px-6 py-4">
          <DialogTitle>eRSV {ersvNumber ?? ''}</DialogTitle>
          {state.kind === 'ready' && (
            <DialogDescription className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              <span>{state.metadata.supplier_name}</span>
              <span aria-hidden="true">·</span>
              <span>{state.metadata.entry_date}</span>
              <span aria-hidden="true">·</span>
              <span>{fmtKg(state.metadata.total_input_kg)} kg</span>
              {/* HIDDEN 2026-05-26 — regenerated chip per direct request
              {state.metadata.is_regenerated && (
                <span className="bg-accent/15 text-accent px-2 py-0.5">regenerated</span>
              )} */}
            </DialogDescription>
          )}
        </DialogHeader>

        <div className="overflow-auto bg-bg-soft min-h-[50vh]">
          {state.kind === 'ready' && (
            <SyntheticRenderBanner entryDate={state.metadata.entry_date} />
          )}
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
              title={`eRSV ${ersvNumber} preview`}
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
