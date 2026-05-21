# RTFO-310825 — OisteBio DEV-P100 Track A Bundle

**Reporting period:** 2025-01-01 to 2025-08-31 (8 months)
**Submission ref:** RTFO-310825
**Generated:** 2026-05-21
**Off-taker / submitter of record:** Crown Oil UK (sole ROS submitter; OisteBio does not submit to DfT directly)
**Feedstock:** ELT (end-of-life tyres) → pyrolysis oil → refined DEV-P100
**RCF eligibility:** UK only, audit-gated (no separate DfT designation; audit pass = eligibility for the batch)

## Contents (59 hashed artefacts)

| Folder | Files | Notes |
|--------|-------|-------|
| `00_cover_letter/` | `00_cover_letter_FINAL.pdf` | 8-month scope, ELT/RCF framing, Crown Oil routing, DB-driven totals |
| `01_annex_a_mass_balance/` | `02_mass_balance_<month>_2025_FINAL.pdf` × 8 | One Annex A per month (Jan-Aug); per-month EU+PLUS densities |
| `02_ros_export/` | `05_production_conversion_logs_<month>_2025.pdf` × 8 | Monthly EU+PLUS per-day kg→L conversion (per-month density) |
| `03_supplier_evidence/` | `03_iscc_pos_status.pdf` + `certificates/` × 15 ISCC PDFs + `contracts/` × 7 + `transport/` × 3 | ISCC PoS status snapshot (volume-weighted cert per supplier); 15 supplier ISCC EU + ISCC PLUS certificate PDFs in `certificates/` (incl. 5 ≤5 TON / pre-rename suppliers (BIOWASTE, ECOGRAS, ECODIESEL, LITOPLAS, SANIMAX)); `contracts/` = 7 supplier contract PDFs (3 signed originals: ESENTTIA, BIOWASTE, LITOPLAS + 4 generated drafts: BOLDER, EFFICIEN, KALTIRE, PYRCOM — qty aligned to migration 0016 redistribution); `transport/` = 2 outbound BL (CMA CGM, CARTAGENA EXPRES 2025-06-11 + ISTANBUL EXPRES 2025-07-03) + `transport_note.md` documenting Jan–May 2025 pre-export stockpile, NL→UK routing chain, and inbound-transport pending status; `ersv/` still gitkeep placeholder pending supplier upload |
| `04_compliance/` | `01_supply_chain_diagram.pdf` + `iscc_eu_certificate/OISTEBIO - EU-ISCC-Cert-LV227-00000597.pdf` + `rtfo_pathway_declaration/08_rtfo_pathway_declaration_FINAL.pdf` | Supplier list + ISCC EU certificate references (no ANLA pathway — ELT RCF is UK RTFO + ISCC EU only); OisteBio ISCC EU certificate LV227-00000597 (issuer CB LV227) covering DEV-P100 producer scope; signed RTFO RCF pathway declaration (Paolo Ughetti, Managing Director) citing ISCC EU System Document 203 + UK RTFO Chapter 9 |
| `05_audit_trail/` | `06_audit_trail_export_<month>_2025.csv` × 8 + `06_audit_trail_redistribution_0016.csv` + `db_snapshots/dft_snapshot_2026-05-21_RTFO-310825.sql` | audit_log diff per month, 0016 supplier-redistribution trail (1,239 rows pre/post per row — `daily_inputs.original_values` materialised), full DB snapshot at submission date |
| `06_annex_d_stock_carryover/` | `07_stock_carryover_jan_feb_2025.pdf` | Documents the 339,865 kg Jan→Feb stock carry-over (Feb 1-4 consumption) |
| (root) | `09_evidence_index_FINAL.pdf` | Evidence index — catalogues every hashed deliverable item |
| (root) | `MANIFEST.sha256` | SHA-256 of every artefact in this bundle |
| (root) | `MANIFEST.sha256.sig` | SHA-256 of `MANIFEST.sha256` itself (root-of-trust hash) |

## Verifying integrity

```bash
cd RTFO-310825
shasum -a 256 -c MANIFEST.sha256
shasum -a 256 MANIFEST.sha256   # compare against MANIFEST.sha256.sig content
```

## Source data fingerprint

- Postgres database `dft`, alembic head `0016`
- Migration history covering Feb-Aug EU% rebalance (0012), gas_syngas density + m³ MV (0013), monthly EU+PLUS densities (0014), PYRCOM orphan cert assignment (0015), Feb-Aug supplier-mix redistribution (0016: EFFICIEN 35% / KALTIRE 30% / PYRCOM 20% / BOLDER 10% / ESENTTIA 5%) — all captured in `05_audit_trail/db_snapshots/`
- All per-row rewrites under 0010/0012/0015 captured in `audit_log` with full `old_values`/`new_values` JSONB; 0016 stores its pre-state on each affected `daily_inputs` row in the `original_values` JSONB column with marker `redistribution_migration: '0016'` for full reversibility via downgrade; the per-month CSV exports replay those rows

## Known gaps (handover items, not blockers)

- `03_supplier_evidence/certificates/` — 15 ISCC certificate PDFs uploaded from internal Drive (2026-05-21); `contracts/` populated 2026-05-21 with 7 supplier contracts (3 signed originals + 4 drafts qty-aligned to migration 0016); `ersv/` still empty until suppliers upload originals
- `03_supplier_evidence/transport/` — 2 outbound BL + corrected arrivals tracker added 2026-05-21; **inbound transport** (suppliers → Girardot weighbridge tickets / CMRs) still pending digital upload from operator — paper records held at Girardot gate-house, retrievable on auditor demand per delivery
- `04_compliance/iscc_eu_certificate/` — OisteBio ISCC EU cert LV227-00000597 uploaded 2026-05-21; `04_compliance/rtfo_pathway_declaration/` populated 2026-05-21 with signed RCF pathway declaration `08_rtfo_pathway_declaration_FINAL.pdf` (Paolo Ughetti, Managing Director; ISCC EU System Document 203 + UK RTFO Chapter 9)
- PYRCOM feedstock mismatch flagged in migration 0010 (cert-correction) remains unresolved; documented in `03_iscc_pos_status.pdf`
- BIOWASTE cert `PL21990602701` format preserved verbatim (no hyphen) — original form retained for ISCC EU audit trail per project policy

## Routing

Bundle hand-off: OisteBio → Crown Oil UK → DfT (ROS portal + LCF Delivery Unit).
OisteBio does **not** submit, communicate, or hold RTFC accounts directly.

## Regenerating the bundle

PDFs are deterministic (fixed `generated_at`, full-font embed). To re-render after a DB change:

```bash
# from repo root
for m in 2025-01 2025-02 2025-03 2025-04 2025-05 2025-06 2025-07 2025-08; do
  python3 scripts/render_annex_a_final.py --period "$m"
  python3 scripts/render_production_conversion_log.py --period "$m"
done
python3 scripts/render_iscc_pos_status.py
python3 scripts/render_supply_chain.py
python3 scripts/render_stock_carryover.py
python3 scripts/render_cover_letter_v2.py
python3 scripts/render_pathway_declaration.py
python3 scripts/render_evidence_index_v2.py      # must run last — indexes all sibling files

# regen MANIFEST + sig
cd deliverables/RTFO-310825
find . -type f \( -name '*.pdf' -o -name '*.csv' -o -name '*.sql' -o -name '*.md' \) -not -name '*.sha256*' -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
sha256sum MANIFEST.sha256 | awk '{print $1}' > MANIFEST.sha256.sig
```
