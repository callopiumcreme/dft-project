'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useOceanBlModal } from './ocean-bl-modal-provider';
import type { OceanBlHeader } from './ocean-bl-modal';

const CONSIGNMENT_ID_RE = /^\d{1,9}$/;
// Ocean BL: SCAC (4 uppercase) + 6–12 digits — mirrors backend regex.
const BL_OCEAN_RE = /^[A-Z]{4}\d{6,12}$/;

interface Props {
  consignmentId: number;
  header: OceanBlHeader;
  className?: string;
  children?: React.ReactNode;
}

export function OceanBlLink({
  consignmentId,
  header,
  className,
  children,
}: Props) {
  const { open } = useOceanBlModal();
  const validCid =
    Number.isInteger(consignmentId) && CONSIGNMENT_ID_RE.test(String(consignmentId));
  const validBl = BL_OCEAN_RE.test(header.blNo);

  if (!validCid || !validBl) {
    return <span className={className}>{children ?? 'BL PDF'}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(consignmentId, header)}
      aria-label={`Open Ocean BL ${header.blNo}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {children ?? 'BL PDF'}
    </button>
  );
}
