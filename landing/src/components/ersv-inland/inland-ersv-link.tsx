'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useInlandErsvModal } from './inland-ersv-modal-provider';
import { SHIPMENT_ID_RE } from '@/lib/inland-ersv-client';
import type { InlandErsvHeader } from './inland-ersv-modal';

interface Props {
  shipmentId: number;
  header: InlandErsvHeader;
  className?: string;
  children?: React.ReactNode;
}

export function InlandErsvLink({ shipmentId, header, className, children }: Props) {
  const { open } = useInlandErsvModal();
  const valid =
    Number.isInteger(shipmentId) && SHIPMENT_ID_RE.test(String(shipmentId));

  if (!valid) {
    return <span className={className}>{children ?? 'Render'}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(shipmentId, header)}
      aria-label={`Open inland eRSV for container ${header.containerId}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {children ?? 'Render'}
    </button>
  );
}
