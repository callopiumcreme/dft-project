/**
 * Paper-records redistribution window — single source of truth.
 *
 * The Jan-Aug 2025 period during which weighbridge-ticket and inbound-eRSV
 * personal-data fields (driver name, cédula, plate, transport, signatures,
 * hora de salida, báscula operator) are rendered by
 * `app.services.ersv_pool` (see migration 0017) against the paper archive
 * retained at OisteBio Girardot. Disclosure surfaces (synthetic-render
 * banner, `/app/reports/by-supplier` view, CSV exports) bind to this
 * window; the countersigned statement at
 * `docs/audit-dft-c1-paper-records-statement.md` is the legal artefact.
 *
 * Round-2 finding N1 — when the audit window was hard-coded inside each
 * consumer (banner, CSV route, dashboard scope, …) it drifted out of date
 * whenever a new consignment crossed the boundary. Centralising here means
 * a single edit before deploy widens or shrinks every disclosure surface
 * at once.
 *
 * Round-3 finding N6 — extending the window start to 2025-01-01 brings
 * January 2025 rows (209 daily_inputs entries) inside the disclosure
 * boundary. The original DfT submission covering that period was rejected
 * for compliance gaps; the current redistribution restates the same
 * paper-archive figures under the corrected framework, so the same
 * banner-and-statement disclosure protocol applies.
 *
 * To extend the window for a new consignment, update WINDOW_END_ISO (or
 * WINDOW_START_ISO) below and ship. No other file should reference these
 * bounds as raw string literals — import them from this module instead.
 */

export const WINDOW_START_ISO = '2025-01-01';
export const WINDOW_END_ISO = '2025-08-31';

/**
 * Returns true when `entryDate` (ISO YYYY-MM-DD) falls inside the window
 * (inclusive on both ends). Returns false for empty / null / undefined.
 */
export function isInPaperRecordsWindow(
  entryDate: string | null | undefined,
): boolean {
  if (!entryDate) return false;
  return entryDate >= WINDOW_START_ISO && entryDate <= WINDOW_END_ISO;
}

/**
 * Derives a short human label from the configured bounds, e.g. "Feb-Aug
 * 2025" when the window spans Feb..Aug of a single year, or
 * "Feb 2025 – Mar 2026" when it crosses a year boundary. Uses
 * `en-GB` short-month formatting for stability against locale drift.
 */
export function formatPaperRecordsWindowLabel(): string {
  const start = new Date(`${WINDOW_START_ISO}T00:00:00Z`);
  const end = new Date(`${WINDOW_END_ISO}T00:00:00Z`);
  const monthFmt = new Intl.DateTimeFormat('en-GB', {
    month: 'short',
    timeZone: 'UTC',
  });
  const startMonth = monthFmt.format(start);
  const endMonth = monthFmt.format(end);
  const startYear = start.getUTCFullYear();
  const endYear = end.getUTCFullYear();
  if (startYear === endYear) {
    return `${startMonth}-${endMonth} ${startYear}`;
  }
  return `${startMonth} ${startYear} – ${endMonth} ${endYear}`;
}
