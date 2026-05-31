'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useProductPurchaseModal } from './product-purchase-modal-provider';
import { POS_NUMBER_RE } from '@/lib/product-purchase-client';

interface Props {
  ppId: number;
  posNumber: string;
  className?: string;
}

export function ProductPurchaseLink({ ppId, posNumber, className }: Props) {
  const { open } = useProductPurchaseModal();
  const valid = POS_NUMBER_RE.test(posNumber);

  if (!valid) {
    return <span className={className}>{posNumber}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(ppId, posNumber)}
      aria-label={`Open PoS ${posNumber}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {posNumber}
    </button>
  );
}
