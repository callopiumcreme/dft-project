'use client';

import * as React from 'react';
import { CustomsEadModal, type CustomsEadHeader } from './customs-ead-modal';

interface CustomsEadModalContextValue {
  open: (consignmentId: number, header: CustomsEadHeader) => void;
  close: () => void;
}

const Ctx = React.createContext<CustomsEadModalContextValue | null>(null);

export function useCustomsEadModal(): CustomsEadModalContextValue {
  const v = React.useContext(Ctx);
  if (!v) throw new Error('useCustomsEadModal must be used within <CustomsEadModalProvider>');
  return v;
}

interface State {
  consignmentId: number;
  header: CustomsEadHeader;
}

export function CustomsEadModalProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<State | null>(null);

  const open = React.useCallback(
    (consignmentId: number, header: CustomsEadHeader) =>
      setState({ consignmentId, header }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<CustomsEadModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      <CustomsEadModal
        consignmentId={state?.consignmentId ?? null}
        header={state?.header ?? null}
        onClose={close}
      />
    </Ctx.Provider>
  );
}
