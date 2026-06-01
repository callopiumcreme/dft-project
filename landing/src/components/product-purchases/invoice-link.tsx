'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface Props {
  invoice: string;
  file: string;
  aggregate?: boolean;
}

function buildUrl(file: string): string {
  return `/api/product-purchases/invoice-pdf?file=${encodeURIComponent(file)}`;
}

export function InvoiceLink({ invoice, file, aggregate }: Props) {
  const [open, setOpen] = React.useState(false);
  const url = buildUrl(file);

  return (
    <>
      <span className="inline-flex items-center gap-1.5 text-ink">
        <button
          type="button"
          onClick={() => {
            window.trackEvent?.('doc_pdf_view', { entity: 'supplier_invoice', invoice });
            setOpen(true);
          }}
          title={aggregate ? `${file} · month-aggregate invoice` : file}
          className="font-medium underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive"
        >
          {invoice}
        </button>
        {aggregate && (
          <span className="border border-rule px-1 py-0.5 text-[0.6rem] uppercase tracking-wide text-ink-mute">
            agg
          </span>
        )}
      </span>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
          <DialogHeader className="border-b border-rule px-6 py-4">
            <DialogTitle>Invoice {invoice}</DialogTitle>
            <DialogDescription className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              {file}
              {aggregate && (
                <>
                  <span aria-hidden="true"> · </span>
                  <span>month-aggregate</span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="overflow-auto bg-bg-soft min-h-[50vh]">
            <iframe
              title={`Invoice ${invoice} preview`}
              src={`${url}#toolbar=0&navpanes=0&view=FitH`}
              className="block h-[70vh] w-full border-0 bg-white"
            />
          </div>

          <DialogFooter className="border-t border-rule px-6 py-4">
            <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
              Close
            </Button>
            <Button variant="primary" size="sm" asChild>
              <a href={url} target="_blank" rel="noopener noreferrer">
                Open in new tab
              </a>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
