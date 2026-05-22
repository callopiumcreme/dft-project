'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useTicketModal } from './ticket-modal-provider';

interface Props {
  dailyInputId: number;
  className?: string;
}

export function TicketLink({ dailyInputId, className }: Props) {
  const { open } = useTicketModal();

  return (
    <button
      type="button"
      onClick={() => open(dailyInputId)}
      aria-label={`Open ticket ${dailyInputId}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      ticket
    </button>
  );
}
