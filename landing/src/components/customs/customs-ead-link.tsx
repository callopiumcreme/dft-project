'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useCustomsEadModal } from './customs-ead-modal-provider';
import type { CustomsEadHeader } from './customs-ead-modal';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
const MRN_RE = /^[0-9A-Z]{18}$/;

interface Props {
  consignmentId: number;
  header: CustomsEadHeader;
  className?: string;
  children?: React.ReactNode;
}

export function CustomsEadLink({ consignmentId, header, className, children }: Props) {
  const { open } = useCustomsEadModal();
  const validCid =
    Number.isInteger(consignmentId) && CONSIGNMENT_ID_RE.test(String(consignmentId));
  const validMrn = MRN_RE.test(header.mrn);

  if (!validCid || !validMrn) {
    return <span className={className}>{children ?? 'Open'}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(consignmentId, header)}
      aria-label={`Open EAD ${header.mrn}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {children ?? 'Open'}
    </button>
  );
}
