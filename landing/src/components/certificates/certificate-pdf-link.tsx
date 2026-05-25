'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { useCertificatePdfModal } from './certificate-pdf-modal-provider';
import type { CertificatePdfHeader } from './certificate-pdf-modal';

const CERT_ID_RE = /^\d{1,9}$/;

interface Props {
  certId: number;
  header: CertificatePdfHeader;
  className?: string;
  children?: React.ReactNode;
}

/**
 * Trigger for the certificate PDF popup (DFTEN-178 / E8-F5).
 *
 * Renders a button styled like the BL / EAD / Invoice "PDF" chip
 * across the app. When clicked, opens the auth-gated iframe modal
 * that streams `/api/certificates/<id>/pdf`. If the id fails the
 * shape check, falls through to a plain (non-clickable) span so the
 * surrounding layout stays stable.
 */
export function CertificatePdfLink({
  certId,
  header,
  className,
  children,
}: Props) {
  const { open } = useCertificatePdfModal();
  const validCid = Number.isInteger(certId) && CERT_ID_RE.test(String(certId));

  if (!validCid) {
    return <span className={className}>{children ?? 'PDF'}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => open(certId, header)}
      aria-label={`Open certificate ${header.certNumber}`}
      className={cn(
        'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive',
        className,
      )}
    >
      {children ?? 'PDF'}
    </button>
  );
}
