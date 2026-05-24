'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useOutboundErsvModal } from './outbound-ersv-modal-provider';
import { CONSIGNMENT_ID_RE, POS_NUMBER_RE } from '@/lib/ersv-outbound-client';
import type { OutboundErsvHeader } from './outbound-ersv-modal';

interface Props {
  consignmentId: number;
  posNumber: string;
  header: OutboundErsvHeader;
  className?: string;
  children?: React.ReactNode;
}

export function OutboundErsvLink({
  consignmentId,
  posNumber,
  header,
  className,
  children,
}: Props) {
  const { open } = useOutboundErsvModal();
  const validCid =
    Number.isInteger(consignmentId) && CONSIGNMENT_ID_RE.test(String(consignmentId));
  const validPos = POS_NUMBER_RE.test(posNumber);

  if (!validCid || !validPos) {
    return <span className={className}>{children ?? 'Render'}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(consignmentId, posNumber, header)}
      aria-label={`Open outbound eRSV for ${posNumber}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {children ?? 'Render'}
    </button>
  );
}
