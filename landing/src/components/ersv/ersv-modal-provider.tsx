'use client';

import * as React from 'react';
import { ErsvModal } from './ersv-modal';

interface ErsvModalContextValue {
  open: (ersvNumber: string, dailyInputId?: number | null) => void;
  close: () => void;
}

const ErsvModalContext = React.createContext<ErsvModalContextValue | null>(null);

export function useErsvModal(): ErsvModalContextValue {
  const ctx = React.useContext(ErsvModalContext);
  if (!ctx) {
    throw new Error('useErsvModal must be used within <ErsvModalProvider>');
  }
  return ctx;
}

interface ErsvModalState {
  ersvNumber: string;
  dailyInputId: number | null;
}

export function ErsvModalProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<ErsvModalState | null>(null);

  const open = React.useCallback(
    (value: string, dailyInputId?: number | null) =>
      setState({ ersvNumber: value, dailyInputId: dailyInputId ?? null }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<ErsvModalContextValue>(() => ({ open, close }), [open, close]);

  return (
    <ErsvModalContext.Provider value={value}>
      {children}
      <ErsvModal
        ersvNumber={state?.ersvNumber ?? null}
        dailyInputId={state?.dailyInputId ?? null}
        onClose={close}
      />
    </ErsvModalContext.Provider>
  );
}
