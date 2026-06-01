'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useC14CertificateModal } from './c14-certificate-modal-provider';
import { C14_NUMBER_RE } from '@/lib/c14-certificate-client';

interface Props {
  c14Id: number;
  certNumber: string;
  className?: string;
}

export function C14CertificateLink({ c14Id, certNumber, className }: Props) {
  const { open } = useC14CertificateModal();
  const valid = C14_NUMBER_RE.test(certNumber);

  if (!valid) {
    return <span className={className}>{certNumber}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(c14Id, certNumber)}
      aria-label={`Open C14 certificate ${certNumber}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {certNumber}
    </button>
  );
}
