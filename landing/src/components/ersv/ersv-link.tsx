'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useErsvModal } from './ersv-modal-provider';
import { ERSV_NUMBER_RE } from '@/lib/ersv-client';

interface Props {
  ersvNumber: string;
  dailyInputId?: number | null;
  className?: string;
}

export function ErsvLink({ ersvNumber, dailyInputId, className }: Props) {
  const { open } = useErsvModal();
  const valid = ERSV_NUMBER_RE.test(ersvNumber);

  if (!valid) {
    return <span className={className}>{ersvNumber}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(ersvNumber, dailyInputId)}
      aria-label={`Open eRSV ${ersvNumber}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {ersvNumber}
    </button>
  );
}
