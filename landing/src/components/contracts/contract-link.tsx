'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useContractModal } from './contract-modal-provider';
import { CONTRACT_CODE_RE } from '@/lib/contract-client';

interface Props {
  contractId: number;
  contractCode: string;
  className?: string;
}

export function ContractLink({ contractId, contractCode, className }: Props) {
  const { open } = useContractModal();
  const valid = CONTRACT_CODE_RE.test(contractCode);

  if (!valid) {
    return <span className={className}>{contractCode}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(contractId, contractCode)}
      aria-label={`Open contract ${contractCode}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {contractCode}
    </button>
  );
}
