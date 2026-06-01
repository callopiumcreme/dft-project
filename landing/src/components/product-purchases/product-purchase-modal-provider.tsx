'use client';

import * as React from 'react';
import { ProductPurchaseModal } from './product-purchase-modal';

interface ProductPurchaseModalContextValue {
  open: (ppId: number, posNumber: string) => void;
  close: () => void;
}

const ProductPurchaseModalContext =
  React.createContext<ProductPurchaseModalContextValue | null>(null);

export function useProductPurchaseModal(): ProductPurchaseModalContextValue {
  const ctx = React.useContext(ProductPurchaseModalContext);
  if (!ctx) {
    throw new Error(
      'useProductPurchaseModal must be used within <ProductPurchaseModalProvider>',
    );
  }
  return ctx;
}

interface ProductPurchaseModalState {
  ppId: number;
  posNumber: string;
}

export function ProductPurchaseModalProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [state, setState] = React.useState<ProductPurchaseModalState | null>(null);

  const open = React.useCallback((ppId: number, posNumber: string) => {
    window.trackEvent?.('doc_pdf_view', { entity: 'product_purchase', id: ppId });
    setState({ ppId, posNumber });
  }, []);
  const close = React.useCallback(() => setState(null), []);

  const value = React.useMemo<ProductPurchaseModalContextValue>(
    () => ({ open, close }),
    [open, close],
  );

  return (
    <ProductPurchaseModalContext.Provider value={value}>
      {children}
      <ProductPurchaseModal
        ppId={state?.ppId ?? null}
        posNumber={state?.posNumber ?? null}
        onClose={close}
      />
    </ProductPurchaseModalContext.Provider>
  );
}
