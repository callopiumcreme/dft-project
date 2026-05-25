'use client';

import * as React from 'react';
import Link from 'next/link';
import { useOutboundErsvModal } from '@/components/ersv-outbound';
import { useCustomsInvoiceModal } from '@/components/invoices';

/**
 * Doc-class router for the warehouse movements ref_doc_no column
 * (DFTEN-181 / E8-F8).
 *
 * Each ledger row carries a free-text ref_doc_no plus (when applicable)
 * the parent consignment_id. We classify ref_doc_no by prefix and surface
 * the matching modal the rest of the app already wires through AppShell:
 *
 *   OISCRO-NNNN-YY     PoS / outbound eRSV     → OutboundErsv modal
 *   INV-*              Customs invoice         → CustomsInvoice modal
 *                                                (only when consignment_id is set
 *                                                — byproduct_sale invoices have
 *                                                no consignment context yet)
 *   DEL-CRW-YYYY-N     Crown Oil delivery doc  → /app/logistics/<consignment_id>
 *   LEGION-QA-*        synthetic test refs     → plain text
 *
 * If the prefix is unknown OR the prerequisites for the modal are
 * missing (no consignment_id where required, doc id fails shape check),
 * we fall through to a plain monospace span so the table layout stays
 * stable. Detail-page navigation via consignment_id is still offered
 * as a last-resort fallback whenever the ref is unrecognised but the
 * row is tied to a consignment.
 */

const POS_RE = /^OISCRO-\d{4}-\d{2}$/;
const INV_RE = /^INV-[A-Z0-9_-]{1,32}$/i;
const DEL_RE = /^DEL-[A-Z0-9_-]{1,32}$/i;
const LEGION_QA_RE = /^LEGION-QA-/;

const CHIP_BASE =
  'underline decoration-dotted underline-offset-2 text-olive-deep hover:text-ink ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-olive';

interface Props {
  refDocNo: string | null;
  consignmentId: number | null;
  productKind?: string | null;
}

export function WarehouseRefDocLink({
  refDocNo,
  consignmentId,
  productKind,
}: Props) {
  const { open: openOutboundErsv } = useOutboundErsvModal();
  const { open: openInvoice } = useCustomsInvoiceModal();

  if (!refDocNo) return <span className="text-ink-mute">—</span>;

  // Synthetic QA refs — never interactive.
  if (LEGION_QA_RE.test(refDocNo)) {
    return <span className="text-ink-soft">{refDocNo}</span>;
  }

  if (POS_RE.test(refDocNo) && consignmentId !== null) {
    return (
      <button
        type="button"
        onClick={() =>
          openOutboundErsv(consignmentId, refDocNo, {
            offTakerCode: null,
            posNumber: refDocNo,
            kgNet: null,
            ersvOutboundNo: null,
            prodDateFrom: null,
            prodDateTo: null,
          })
        }
        aria-label={`Open outbound eRSV for ${refDocNo}`}
        className={CHIP_BASE}
      >
        {refDocNo}
      </button>
    );
  }

  if (INV_RE.test(refDocNo) && consignmentId !== null) {
    return (
      <button
        type="button"
        onClick={() =>
          openInvoice(consignmentId, {
            posNumber: '',
            invoiceNo: refDocNo,
            mrn: null,
            netKg: null,
            issuingDate: null,
          })
        }
        aria-label={`Open invoice ${refDocNo}`}
        className={CHIP_BASE}
      >
        {refDocNo}
      </button>
    );
  }

  if (DEL_RE.test(refDocNo) && consignmentId !== null) {
    return (
      <Link
        href={`/app/logistics/${consignmentId}`}
        className={CHIP_BASE}
        aria-label={`Open consignment for ${refDocNo}`}
      >
        {refDocNo}
      </Link>
    );
  }

  // Unknown prefix — if we still have a consignment_id, offer detail nav.
  if (consignmentId !== null) {
    return (
      <Link
        href={`/app/logistics/${consignmentId}`}
        className={CHIP_BASE}
        aria-label={`Open consignment ${consignmentId} for ${refDocNo}`}
      >
        {refDocNo}
      </Link>
    );
  }

  // No consignment context and no prefix match — render flat.
  // productKind kept in props for future drill-down (e.g. byproduct sale
  // detail page) without breaking call sites.
  void productKind;
  return <span className="text-ink-soft">{refDocNo}</span>;
}
