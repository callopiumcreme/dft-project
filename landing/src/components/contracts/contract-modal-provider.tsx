'use client';

import * as React from 'react';
import { ContractModal } from './contract-modal';

interface ContractModalContextValue {
  open: (contractId: number, contractCode: string) => void;
  close: () => void;
}

const ContractModalContext = React.createContext<ContractModalContextValue | null>(null);

export function useContractModal(): ContractModalContextValue {
  const ctx = React.useContext(ContractModalContext);
  if (!ctx) {
    throw new Error('useContractModal must be used within <ContractModalProvider>');
  }
  return ctx;
}

interface ContractModalState {
  contractId: number;
  contractCode: string;
}

export function ContractModalProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<ContractModalState | null>(null);

  const open = React.useCallback(
    (contractId: number, contractCode: string) =>
      setState({ contractId, contractCode }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<ContractModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <ContractModalContext.Provider value={value}>
      {children}
      <ContractModal
        contractId={state?.contractId ?? null}
        contractCode={state?.contractCode ?? null}
        onClose={close}
      />
    </ContractModalContext.Provider>
  );
}
