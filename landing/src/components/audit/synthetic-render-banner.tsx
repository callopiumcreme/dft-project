'use client';

/**
 * SyntheticRenderBanner
 *
 * Displays a clearly-visible disclosure banner inside any modal that
 * renders weighbridge-ticket or inbound-eRSV personal-data fields for
 * deliveries dated within the Feb-Aug 2025 redistribution window.
 *
 * Personal-data fields (driver name, cédula, vehicle plate, transport
 * company, hora de salida, signatures, báscula operator) are produced by
 * a deterministic placeholder pool (`app.services.ersv_pool`) and are NOT
 * source-of-truth. The paper-records statement at
 * `docs/audit-dft-c1-paper-records-statement.md` (Paolo Ughetti,
 * Geschäftsführer OisteBio GmbH) is the binding disclosure.
 *
 * The banner renders only when `entryDate` falls between the configured
 * window bounds (inclusive). It renders nothing otherwise (e.g. January
 * 2025 frozen rows; September 2025 and later electronic-capture rows).
 */

import * as React from 'react';

const WINDOW_START_ISO = '2025-02-01';
const WINDOW_END_ISO = '2025-08-31';

interface Props {
  /** ISO date string `YYYY-MM-DD` of the delivery entry (or undefined while loading). */
  entryDate: string | null | undefined;
}

function isInWindow(entryDate: string | null | undefined): boolean {
  if (!entryDate) return false;
  return entryDate >= WINDOW_START_ISO && entryDate <= WINDOW_END_ISO;
}

export function SyntheticRenderBanner({ entryDate }: Props): React.JSX.Element | null {
  if (!isInWindow(entryDate)) return null;
  return (
    <div
      role="note"
      aria-label="Synthetic-rendering disclosure"
      className="border-b border-accent/40 bg-accent/10 px-6 py-3"
    >
      <p className="font-mono text-[0.7rem] uppercase tracking-[0.12em] text-accent">
        Audit disclosure — synthetic rendering
      </p>
      <p className="mt-1 text-[0.72rem] leading-snug text-ink">
        Personal-data fields below (driver, cédula, plate, transport,
        signatures, hora de salida, báscula operator) are{' '}
        <strong>deterministic placeholders</strong> seeded by stable row
        identifiers. They are <strong>not source-of-truth</strong>.
        Source-of-truth records are paper weighbridge tickets and original
        eRSV documents retained at OisteBio Girardot (operator: Zuniga
        Martinez S.A.S.) for the Feb-Aug 2025 redistribution window. See{' '}
        <code className="bg-bg-soft px-1">
          audit-dft-c1-paper-records-statement
        </code>{' '}
        (Paolo Ughetti, Geschäftsführer OisteBio GmbH).
      </p>
    </div>
  );
}
