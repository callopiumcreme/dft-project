'use client';

import * as React from 'react';
import { TicketModal } from './ticket-modal';

interface TicketModalContextValue {
  open: (dailyInputId: number) => void;
  close: () => void;
}

const TicketModalContext = React.createContext<TicketModalContextValue | null>(null);

export function useTicketModal(): TicketModalContextValue {
  const ctx = React.useContext(TicketModalContext);
  if (!ctx) {
    throw new Error('useTicketModal must be used within <TicketModalProvider>');
  }
  return ctx;
}

interface TicketModalState {
  dailyInputId: number;
}

export function TicketModalProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<TicketModalState | null>(null);

  const open = React.useCallback(
    (dailyInputId: number) => setState({ dailyInputId }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<TicketModalContextValue>(() => ({ open, close }), [open, close]);

  return (
    <TicketModalContext.Provider value={value}>
      {children}
      <TicketModal dailyInputId={state?.dailyInputId ?? null} onClose={close} />
    </TicketModalContext.Provider>
  );
}
