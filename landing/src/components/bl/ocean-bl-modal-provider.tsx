'use client';

import * as React from 'react';
import { OceanBlModal, type OceanBlHeader } from './ocean-bl-modal';

interface OceanBlModalContextValue {
  open: (consignmentId: number, header: OceanBlHeader) => void;
  close: () => void;
}

const Ctx = React.createContext<OceanBlModalContextValue | null>(null);

export function useOceanBlModal(): OceanBlModalContextValue {
  const v = React.useContext(Ctx);
  if (!v)
    throw new Error(
      'useOceanBlModal must be used within <OceanBlModalProvider>',
    );
  return v;
}

interface State {
  consignmentId: number;
  header: OceanBlHeader;
}

export function OceanBlModalProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = React.useState<State | null>(null);

  const open = React.useCallback(
    (consignmentId: number, header: OceanBlHeader) =>
      setState({ consignmentId, header }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<OceanBlModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      <OceanBlModal
        consignmentId={state?.consignmentId ?? null}
        header={state?.header ?? null}
        onClose={close}
      />
    </Ctx.Provider>
  );
}
