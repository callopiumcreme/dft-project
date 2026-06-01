'use client';

import * as React from 'react';

interface Props {
  href: string;
  report: string;
  className?: string;
  children: React.ReactNode;
}

/**
 * CSV export anchor that emits a `report_csv_export` Umami event on click.
 *
 * The global FILE_RE download listener misses these links because the CSV
 * endpoint URLs end in `/csv` (no dot extension), so the export is tracked
 * explicitly here. `report` identifies which report was exported.
 */
export function CsvExportLink({ href, report, className, children }: Props) {
  return (
    <a
      href={href}
      className={className}
      download
      onClick={() => {
        window.trackEvent?.('report_csv_export', { report });
      }}
    >
      {children}
    </a>
  );
}
