'use client';

import * as React from 'react';
import {
  CertificatePdfModal,
  type CertificatePdfHeader,
} from './certificate-pdf-modal';

interface CertificatePdfModalContextValue {
  open: (certId: number, header: CertificatePdfHeader) => void;
  close: () => void;
}

const Ctx = React.createContext<CertificatePdfModalContextValue | null>(null);

export function useCertificatePdfModal(): CertificatePdfModalContextValue {
  const v = React.useContext(Ctx);
  if (!v)
    throw new Error(
      'useCertificatePdfModal must be used within <CertificatePdfModalProvider>',
    );
  return v;
}

interface State {
  certId: number;
  header: CertificatePdfHeader;
}

export function CertificatePdfModalProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = React.useState<State | null>(null);

  const open = React.useCallback(
    (certId: number, header: CertificatePdfHeader) =>
      setState({ certId, header }),
    [],
  );
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<CertificatePdfModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      <CertificatePdfModal
        certId={state?.certId ?? null}
        header={state?.header ?? null}
        onClose={close}
      />
    </Ctx.Provider>
  );
}
