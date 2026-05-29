# 04 — Feedstock provider authorisations

**Status:** 🟡 IN PROGRESS — blocked on T1 (OisteBio fornisce copie)
**Owner:** OisteBio (Paolo Ughetti) → handed to DFT team for assembly
**Audit context:** DfT C1 (Deeba Rehman) — DEL-CRW-2025-2 audit window Jan–Aug 2025
**Plane:** DFTEN-108 [E1-S1.14]

---

## Purpose

Provide audit-window feedstock provider authorisation evidence for the three
plastics/organics-era suppliers active during the Jan 2025 window of DEL-CRW-2025-2.
These suppliers retired or were superseded after Feb 2025 when the Girardot plant
pivoted to ELT (end-of-life tyres) feedstock — see memory
`project_feedstock_elt` for the supplier-by-supplier breakdown.

The folder lands inside the audit bundle as a sub-section of point 02 (Feedstock
Delivery Notes) supplementary evidence.

---

## Files expected

| File | Source | Status |
|------|--------|--------|
| `litoplas_ANLA.pdf` | OisteBio → ANLA / Min. Ambiente Colombia (non legalised copy) | ⏳ awaiting from OisteBio |
| `biowaste_ANLA.pdf` | OisteBio → ANLA / Min. Ambiente Colombia (non legalised copy) | ⏳ awaiting from OisteBio |
| `esenttia_ANLA.pdf` | OisteBio → ANLA / Min. Ambiente Colombia (non legalised copy) | ⏳ awaiting from OisteBio |
| `_status_legalisation.pdf` | OisteBio statement on consular legalisation ETA | ⏳ awaiting from OisteBio |

> Files are **non-legalised** Colombian authority copies. Consular legalisation
> ETA captured in `_status_legalisation.pdf` so the auditor can distinguish the
> in-flight legalisation work from the underlying authorisation status.

---

## Why these three suppliers only

The Jan 2025 audit window had four non-ELT suppliers contributing input:

| Supplier | Jan-Aug 2025 | Active period | Feedstock |
|---|---|---|---|
| ESENTTIA | 169 rows / 2,516,029 kg | Jan–Aug | plastic |
| ≤5 TON | 621 rows / 2,466,979 kg | Jan–Aug | mix (self-decl) |
| BIOWASTE | 66 rows / 1,152,775 kg | Jan only | organics |
| LITOPLAS | 34 rows / 600,286 kg | Jan only | plastic |

`≤5 TON` is the self-declaration aggregate bucket (no single legal entity), so
authorisation evidence applies only to ESENTTIA + LITOPLAS + BIOWASTE.

The five ELT-era suppliers (KAL TIRE, EFFICIEN TECHNOLOGY, PYRCOM SAS, BOLDER
INDUSTRIES, SANIMAX / CIECOGRAS / ECODIESEL where applicable) are covered in
the main 01 ISCC certificates pack — see
`01_supplier_iscc_contract_coverage.csv`.

---

## Cross-references

- Plane ticket: DFTEN-108 — `[E1-S1.14] Feedstock provider authorisations folder + status`
- Memory: `project_feedstock_elt` (going-forward ELT vs audit-window mixed)
- Memory: `project_iscc_audit_safety` (preserve historical doc IDs verbatim)
- Audit bundle root: `landing/public/audit/DfT_Audit_Submission.zip`
- Sister doc: `docs/audit-dft-c1-deeba-realign/2026-05-28-en-realign-summary.md`

---

## Next actions

1. **OisteBio (Paolo Ughetti)** — provide PDF scans for the four `⏳` rows above.
2. **DFT team** — once received, drop PDFs into this folder verbatim (no
   re-naming of supplier-issued document IDs — ISCC audit safety rule).
3. **DFT team** — fold the folder into the next audit bundle rebuild + update
   `01_supplier_iscc_contract_coverage.csv` row notes to reference this folder.
4. **Close DFTEN-108** when all four files are present + audit bundle rebuilt.

---

_Last update: 2026-05-29 — Sprint γ DFTEN-108 skeleton (Claude) — folder created
ahead of OisteBio deliverable so the receive-and-drop step is trivial._
