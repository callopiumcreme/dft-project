'use client';

import * as React from 'react';
import {
  CustomsInvoiceModal,
  type CustomsInvoiceHeader,
} from './customs-invoice-modal';

interface CustomsInvoiceModalContextValue {
  open: (consignmentId: number, header: CustomsInvoiceHeader) => void;
  close: () => void;
}

const Ctx = React.createContext<CustomsInvoiceModalContextValue | null>(null);

export function useCustomsInvoiceModal(): CustomsInvoiceModalContextValue {
  const v = React.useContext(Ctx);
  if (!v)
    throw new Error(
      'useCustomsInvoiceModal must be used within <CustomsInvoiceModalProvider>',
    );
  return v;
}

interface State {
  consignmentId: number;
  header: CustomsInvoiceHeader;
}

export function CustomsInvoiceModalProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = React.useState<State | null>(null);

  const open = React.useCallback(
    (consignmentId: number, header: CustomsInvoiceHeader) =>
      setState({ consignmentId, header }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<CustomsInvoiceModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      <CustomsInvoiceModal
        consignmentId={state?.consignmentId ?? null}
        header={state?.header ?? null}
        onClose={close}
      />
    </Ctx.Provider>
  );
}
