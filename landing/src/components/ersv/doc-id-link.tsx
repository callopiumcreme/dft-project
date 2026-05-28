'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useErsvModal } from './ersv-modal-provider';
import { ERSV_NUMBER_RE } from '@/lib/ersv-client';

interface Props {
  /** Full sha256 hex (64 chars); first 16 are rendered, matches PDF header. */
  docIdHash: string;
  /** eRSV number used to open the same modal as ErsvLink. */
  ersvNumber: string;
  /** Optional daily_input id to disambiguate Feb-Aug 2025 cross-supplier collisions. */
  dailyInputId?: number | null;
  className?: string;
}

/**
 * Clickable Doc ID prefix that opens the same eRSV modal as ErsvLink.
 * Shown next to the eRSV column on the mass-balance day breakdown so
 * auditors can correlate the printed PDF header ("Doc ID xxxxxxxxxxxxxxxx")
 * with the ledger row 1:1.
 */
export function DocIdLink({ docIdHash, ersvNumber, dailyInputId, className }: Props) {
  const { open } = useErsvModal();
  const valid = ERSV_NUMBER_RE.test(ersvNumber) && /^[0-9a-f]{16,64}$/.test(docIdHash);

  const prefix = docIdHash.slice(0, 16);

  if (!valid) {
    return <span className={cn('font-mono text-ink-soft', className)}>{prefix || '—'}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(ersvNumber, dailyInputId)}
      aria-label={`Open eRSV ${ersvNumber} (doc ${prefix})`}
      title={docIdHash}
      className={cn(
        'font-mono underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {prefix}
    </button>
  );
}
