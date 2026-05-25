'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useCustomsInvoiceModal } from './customs-invoice-modal-provider';
import type { CustomsInvoiceHeader } from './customs-invoice-modal';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
const INVOICE_RE = /^OIS-INV\d{4,12}$/;

interface Props {
  consignmentId: number;
  header: CustomsInvoiceHeader;
  className?: string;
  children?: React.ReactNode;
}

export function CustomsInvoiceLink({
  consignmentId,
  header,
  className,
  children,
}: Props) {
  const { open } = useCustomsInvoiceModal();
  const validCid =
    Number.isInteger(consignmentId) && CONSIGNMENT_ID_RE.test(String(consignmentId));
  const validInv = INVOICE_RE.test(header.invoiceNo);

  if (!validCid || !validInv) {
    return <span className={className}>{children ?? 'Invoice'}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(consignmentId, header)}
      aria-label={`Open invoice ${header.invoiceNo}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {children ?? 'Invoice'}
    </button>
  );
}
