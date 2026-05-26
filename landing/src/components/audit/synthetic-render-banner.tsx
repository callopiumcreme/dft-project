'use client';

/**
 * SyntheticRenderBanner
 *
 * Displays a clearly-visible disclosure banner inside any modal that
 * renders weighbridge-ticket or inbound-eRSV personal-data fields for
 * deliveries dated within the paper-records redistribution window
 * (see `@/config/paper-records-window` for the configured bounds; the
 * banner uses `formatPaperRecordsWindowLabel()` to display the live
 * window label rather than hard-coding the period).
 *
 * Personal-data fields inside the window (driver name, cédula, vehicle
 * plate, hora de salida, báscula operator) render the literal marker
 * `[Paper record — Girardot archive]` instead of any plausible value
 * (see `backend/app/services/ersv_pool.py` — Round-3 findings N6 / N7).
 * The marker tells the verifier that those cells are bound to the paper
 * archive retained at OisteBio Girardot (operator: Zuniga Martinez
 * S.A.S.) and are not per-row attestations in this document. The
 * countersigned statement at
 * `docs/audit-dft-c1-paper-records-statement.md` (Paolo Ughetti,
 * Geschäftsführer OisteBio GmbH) is the binding disclosure.
 *
 * The banner renders only when `entryDate` falls between the configured
 * window bounds (inclusive). It renders nothing otherwise (e.g. September
 * 2025 and later electronic-capture rows where the data is real per-row).
 */

import * as React from 'react';

import {
  formatPaperRecordsWindowLabel,
  isInPaperRecordsWindow,
} from '@/config/paper-records-window';

interface Props {
  /** ISO date string `YYYY-MM-DD` of the delivery entry (or undefined while loading). */
  entryDate: string | null | undefined;
}

export function SyntheticRenderBanner({ entryDate }: Props): React.JSX.Element | null {
  if (!isInPaperRecordsWindow(entryDate)) return null;
  const windowLabel = formatPaperRecordsWindowLabel();
  return (
    <div
      role="note"
      aria-label="Synthetic-rendering disclosure"
      className="border-b border-accent/40 bg-accent/10 px-6 py-3"
    >
      <p className="font-mono text-[0.7rem] uppercase tracking-[0.12em] text-accent">
        Audit disclosure — paper-record marker
      </p>
      <p className="mt-1 text-[0.72rem] leading-snug text-ink">
        Personal-data fields below (driver, cédula, plate, hora de salida,
        báscula operator) render the literal marker{' '}
        <code className="bg-bg-soft px-1">
          [Paper record — Girardot archive]
        </code>{' '}
        rather than any per-row value. The marker indicates that each
        such cell is bound to the paper archive retained at OisteBio
        Girardot (operator: Zuniga Martinez S.A.S.) for the {windowLabel}{' '}
        redistribution window — not to a per-row attestation in this
        document. See{' '}
        <code className="bg-bg-soft px-1">
          audit-dft-c1-paper-records-statement
        </code>{' '}
        (Paolo Ughetti, Geschäftsführer OisteBio GmbH) for the
        countersigned disclosure.
      </p>
    </div>
  );
}
