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
  ppId: number;
  posNumber: string;
}

// Click the "require" badge → preview an on-the-fly proforma / supply-data-sheet
// for suppliers whose official invoice is not yet issued. NOT a fiscal invoice;
// price/total/invoice-no are placeholders the supplier completes.
export function ProformaLink({ ppId, posNumber }: Props) {
  const [open, setOpen] = React.useState(false);
  const url = `/api/product-purchases/${ppId}/proforma`;

  return (
    <>
      <button
        type="button"
        onClick={() => {
          window.trackEvent?.('doc_pdf_view', { entity: 'proforma', pos: posNumber });
          setOpen(true);
        }}
        title={`Supply data sheet · ${posNumber}`}
        className="inline-block border border-accent bg-accent/5 px-2 py-0.5 text-[0.65rem] uppercase text-accent hover:bg-accent/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        require
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] grid-rows-[auto_1fr_auto] p-0 overflow-hidden">
          <DialogHeader className="border-b border-rule px-6 py-4">
            <DialogTitle>Supply Data Sheet · {posNumber}</DialogTitle>
            <DialogDescription className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              Supply data sheet · not a fiscal invoice
            </DialogDescription>
          </DialogHeader>

          <div className="overflow-auto bg-bg-soft min-h-[50vh]">
            <iframe
              title={`Supply Data Sheet ${posNumber} preview`}
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
