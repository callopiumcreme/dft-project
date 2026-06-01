// PoS → supplier invoice (FATTURA) association.
//
// Source of truth: client Drive folder
//   DFT_2025/POS E FATTURE MANCANTI/SUPPLIERS/
// containing the supplier sales invoices uploaded for the RTFO audit window.
// Verified 2026-06-01 by reading each invoice PDF and matching issue date +
// quantity (MT/kg) against the product_purchases rows.
//
// Only 3 suppliers have invoices in Drive: ESENTTIA, LITOPLAS, BIOWASTE.
// The four monthly suppliers (BOLDER, EFFICIEN, KALTIRE, PYRCOM) have NO
// invoice uploaded yet → they resolve to `null` (rendered as "Missing").
//
// `aggregate: true` marks a January sub-delivery PoS (≤5 TON self-decl or
// early individual delivery) whose invoice is the single month-aggregate
// invoice — i.e. one invoice legally covers several small PoS.

export interface PosInvoice {
  /** Supplier invoice number as printed on the FATTURA. */
  invoice: string;
  /** Drive file the invoice lives in (under POS E FATTURE MANCANTI/SUPPLIERS/). */
  file: string;
  /** True when the invoice is a month-aggregate covering this + sibling sub-PoS. */
  aggregate?: boolean;
}

const ESENTTIA_FILE = 'esenttia invoices 2025.pdf';
// ESENTTIA per-delivery January invoices (line-item per PoS): 2025-004, 2025-005.
const ESENTTIA_EARLY_FILE = 'Pagine da ESENTTIA.pdf';
const BIOWASTE_FILE = 'FACTURA_BIOWASTE_074.pdf';
const LITOPLAS_FILE = 'FACTURA_LITOPLAS_0224.pdf';
// LITOPLAS per-delivery January invoices (one invoice per early PoS): 25-0078, 25-0170.
const LITOPLAS_EARLY_FILE = 'Pagine da LITOPLAS.pdf';

// Keyed by product_purchases.pos_number (exact).
export const POS_INVOICE_MAP: Record<string, PosInvoice> = {
  // ── ESENTTIA — 8 monthly aggregate invoices (one PDF, 8 pages) ──
  'ES2025-014': { invoice: '2025-035', file: ESENTTIA_FILE }, // Jan agg, 31/01
  'ES2025-019': { invoice: '2025-059', file: ESENTTIA_FILE }, // Feb,     28/02
  'ES2025-027': { invoice: '2025-121', file: ESENTTIA_FILE }, // Mar,     31/03
  'ES2025-036': { invoice: '2025-159', file: ESENTTIA_FILE }, // Apr,     30/04
  'ES2025-047': { invoice: '2025-227', file: ESENTTIA_FILE }, // May,     31/05
  'ES2025-053': { invoice: '2025-311', file: ESENTTIA_FILE }, // Jun,     30/06
  'ES2025-060': { invoice: '2025-399', file: ESENTTIA_FILE }, // Jul,     31/07
  'ES2025-069': { invoice: '2025-434', file: ESENTTIA_FILE }, // Aug,     01/09
  // ESENTTIA January per-delivery PoS → billed line-by-line in the early
  // per-delivery invoices (NOT in monthly aggregate 2025-035). The 16,020 kg
  // first load (ES2025-001) is line 001 of invoice 2025-004; it was removed
  // from the pending 2025-035 by the supplier so the aggregate (014) bills
  // only the 7–31 Jan deliveries. aggregate:true = one invoice covers 5 PoS.
  'ES2025-001': { invoice: '2025-004', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-002': { invoice: '2025-004', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-003': { invoice: '2025-004', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-004': { invoice: '2025-004', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-005': { invoice: '2025-004', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-009': { invoice: '2025-005', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-010': { invoice: '2025-005', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-011': { invoice: '2025-005', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-012': { invoice: '2025-005', file: ESENTTIA_EARLY_FILE, aggregate: true },
  'ES2025-013': { invoice: '2025-005', file: ESENTTIA_EARLY_FILE, aggregate: true },

  // ── BIOWASTE — single January invoice (month total) ──
  '2025-006-OISTEB': { invoice: '2025-074', file: BIOWASTE_FILE }, // Jan agg, 31/01
  // BIOWASTE January individual sub-PoS → covered by aggregate invoice 2025-074
  '2025-001-OISTEB': { invoice: '2025-074', file: BIOWASTE_FILE, aggregate: true },
  '2025-002-OISTEB': { invoice: '2025-074', file: BIOWASTE_FILE, aggregate: true },
  '2025-004-OISTEB': { invoice: '2025-074', file: BIOWASTE_FILE, aggregate: true },
  '2025-005-OISTEB': { invoice: '2025-074', file: BIOWASTE_FILE, aggregate: true },

  // ── LITOPLAS — January ──
  // Two early deliveries billed line-by-line in their own per-delivery invoices
  // (paid via Currenxie 03/06 Jan); these are NOT in the month-aggregate.
  // The aggregate PoS 0011 (whole January) was rebalanced to 565,806 = corrected
  // aggregate invoice 25-0224 (supplier removed the 2,022.43 kg over-bill).
  '01-2025-0004': { invoice: '25-0078', file: LITOPLAS_EARLY_FILE }, // 03/01, 17,200
  '01-2025-0007': { invoice: '25-0170', file: LITOPLAS_EARLY_FILE }, // 06/01, 17,280
  '01-2025-0011': { invoice: '25-0224', file: LITOPLAS_FILE },       // Jan agg, 31/01, 565,806
};

export function posInvoice(posNumber: string | null | undefined): PosInvoice | null {
  if (!posNumber) return null;
  return POS_INVOICE_MAP[posNumber] ?? null;
}
