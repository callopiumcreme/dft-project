'use client';

import * as React from 'react';
import { InlandErsvModal, type InlandErsvHeader } from './inland-ersv-modal';

interface InlandErsvModalContextValue {
  open: (shipmentId: number, header: InlandErsvHeader) => void;
  close: () => void;
}

const InlandErsvModalContext = React.createContext<InlandErsvModalContextValue | null>(null);

export function useInlandErsvModal(): InlandErsvModalContextValue {
  const ctx = React.useContext(InlandErsvModalContext);
  if (!ctx) {
    throw new Error('useInlandErsvModal must be used within <InlandErsvModalProvider>');
  }
  return ctx;
}

interface InlandErsvModalState {
  shipmentId: number;
  header: InlandErsvHeader;
}

export function InlandErsvModalProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<InlandErsvModalState | null>(null);

  const open = React.useCallback(
    (shipmentId: number, header: InlandErsvHeader) =>
      setState({ shipmentId, header }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<InlandErsvModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <InlandErsvModalContext.Provider value={value}>
      {children}
      <InlandErsvModal
        shipmentId={state?.shipmentId ?? null}
        header={state?.header ?? null}
        onClose={close}
      />
    </InlandErsvModalContext.Provider>
  );
}
