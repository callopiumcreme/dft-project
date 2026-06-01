'use client';

import * as React from 'react';
import { C14CertificateModal } from './c14-certificate-modal';

interface C14CertificateModalContextValue {
  open: (c14Id: number, certNumber: string) => void;
  close: () => void;
}

const C14CertificateModalContext =
  React.createContext<C14CertificateModalContextValue | null>(null);

export function useC14CertificateModal(): C14CertificateModalContextValue {
  const ctx = React.useContext(C14CertificateModalContext);
  if (!ctx) {
    throw new Error(
      'useC14CertificateModal must be used within <C14CertificateModalProvider>',
    );
  }
  return ctx;
}

interface C14CertificateModalState {
  c14Id: number;
  certNumber: string;
}

export function C14CertificateModalProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = React.useState<C14CertificateModalState | null>(null);

  const open = React.useCallback((c14Id: number, certNumber: string) => {
    window.trackEvent?.('doc_pdf_view', { entity: 'c14_certificate', id: c14Id });
    setState({ c14Id, certNumber });
  }, []);
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<C14CertificateModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <C14CertificateModalContext.Provider value={value}>
      {children}
      <C14CertificateModal
        c14Id={state?.c14Id ?? null}
        certNumber={state?.certNumber ?? null}
        onClose={close}
      />
    </C14CertificateModalContext.Provider>
  );
}
