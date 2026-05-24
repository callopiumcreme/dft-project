'use client';

import * as React from 'react';
import { OutboundErsvModal, type OutboundErsvHeader } from './outbound-ersv-modal';

interface OutboundErsvModalContextValue {
  open: (consignmentId: number, posNumber: string, header: OutboundErsvHeader) => void;
  close: () => void;
}

const OutboundErsvModalContext = React.createContext<OutboundErsvModalContextValue | null>(null);

export function useOutboundErsvModal(): OutboundErsvModalContextValue {
  const ctx = React.useContext(OutboundErsvModalContext);
  if (!ctx) {
    throw new Error('useOutboundErsvModal must be used within <OutboundErsvModalProvider>');
  }
  return ctx;
}

interface OutboundErsvModalState {
  consignmentId: number;
  posNumber: string;
  header: OutboundErsvHeader;
}

export function OutboundErsvModalProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<OutboundErsvModalState | null>(null);

  const open = React.useCallback(
    (consignmentId: number, posNumber: string, header: OutboundErsvHeader) =>
      setState({ consignmentId, posNumber, header }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<OutboundErsvModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <OutboundErsvModalContext.Provider value={value}>
      {children}
      <OutboundErsvModal
        consignmentId={state?.consignmentId ?? null}
        posNumber={state?.posNumber ?? null}
        header={state?.header ?? null}
        onClose={close}
      />
    </OutboundErsvModalContext.Provider>
  );
}
