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
  fetchTicketMetadata,
  buildTicketEscposUrl,
  TicketNotFoundError,
  type TicketDetail,
} from '@/lib/ticket-client';
import { SyntheticRenderBanner } from '@/components/audit/synthetic-render-banner';

interface Props {
  dailyInputId: number | null;
  onClose: () => void;
}

type LoadState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready'; metadata: TicketDetail }
  | { kind: 'error'; message: string; status?: number };

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });

function fmtKg(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return '—';
  return numFmt.format(n);
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-rule/40 py-1.5 last:border-b-0">
      <span className="text-ink-mute uppercase tracking-[0.1em]">{label}</span>
      <span className="text-ink text-right tabular-nums">{value}</span>
    </div>
  );
}

export function TicketModal({ dailyInputId, onClose }: Props) {
  const [state, setState] = React.useState<LoadState>({ kind: 'idle' });
  const [attempt, setAttempt] = React.useState(0);

  const isOpen = dailyInputId !== null;

  React.useEffect(() => {
    if (dailyInputId === null) {
      setState({ kind: 'idle' });
      return;
    }

    let cancelled = false;
    setState({ kind: 'loading' });

    fetchTicketMetadata(dailyInputId)
      .then((metadata) => {
        if (cancelled) return;
        setState({ kind: 'ready', metadata });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof TicketNotFoundError) {
          setState({
            kind: 'error',
            message: `Ticket ${dailyInputId} not found`,
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
  }, [dailyInputId, attempt]);

  const handleOpenChange = (next: boolean) => {
    if (!next) onClose();
  };

  const handleRetry = () => setAttempt((n) => n + 1);

  const escposUrl = dailyInputId !== null ? buildTicketEscposUrl(dailyInputId) : '#';

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
        <DialogHeader className="border-b border-rule px-6 py-4">
          <DialogTitle>
            Ticket {state.kind === 'ready' ? `#${state.metadata.ticket_num}` : ''}
          </DialogTitle>
          {state.kind === 'ready' && (
            <DialogDescription className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              <span>{state.metadata.supplier_name}</span>
              <span aria-hidden="true">·</span>
              <span>{state.metadata.entry_date}</span>
              <span aria-hidden="true">·</span>
              <span>{fmtKg(state.metadata.peso_neto_kg)} kg</span>
              <span aria-hidden="true">·</span>
              <span>{state.metadata.prod}</span>
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
                Loading ticket…
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
            <div className="p-6 space-y-6">
              <div className="grid gap-0 font-mono text-[0.72rem]">
                <Row label="eRSV" value={state.metadata.ersv_number ?? '—'} />
                <Row
                  label="Supplier"
                  value={`${state.metadata.supplier_code} · ${state.metadata.supplier_name}`}
                />
                <Row label="Prod" value={state.metadata.prod} />
                <Row label="Driver" value={state.metadata.driver_name} />
                <Row label="Cédula" value={state.metadata.driver_cedula} />
                <Row label="Plate" value={state.metadata.vehicle_plate} />
                <Row label="Transport" value={state.metadata.transport_company} />
                <Row label="Hora ent." value={state.metadata.hora_ent} />
                <Row label="Hora sal." value={state.metadata.hora_sal} />
                <Row label="Peso ent." value={`${fmtKg(state.metadata.peso_ent_kg)} kg`} />
                <Row label="Peso sal." value={`${fmtKg(state.metadata.peso_sal_kg)} kg`} />
                <Row label="Peso neto" value={`${fmtKg(state.metadata.peso_neto_kg)} kg`} />
                <Row label="Total input" value={`${fmtKg(state.metadata.total_input_kg)} kg`} />
                <Row label="Weigher" value={state.metadata.weigher} />
              </div>
              <pre className="font-mono text-[0.72rem] leading-snug whitespace-pre-wrap border border-rule bg-white px-4 py-3 text-ink">
                {state.metadata.preview_text}
              </pre>
            </div>
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
              href={state.kind === 'ready' ? escposUrl : undefined}
              download
              onClick={(e) => {
                if (state.kind !== 'ready') e.preventDefault();
              }}
            >
              Stampa termica
            </a>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
