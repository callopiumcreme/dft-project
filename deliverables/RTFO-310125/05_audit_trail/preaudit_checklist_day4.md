# Pre-audit Bundle Day 4 — RTFO-310125 (S1.15 / DFTEN-109)

**Date:** 2026-05-20 (Day 6 of 7-day Track A window; pre-audit retroactively executed on Day 6 due to consolidated Day 4-6 work).
**Bundle:** `deliverables/RTFO-310125/`
**Walkthrough team:** team ingest (digital), OisteBio (compliance), Crown Oil (legal).
**Reference specs:**
- `docs/dft-action-plan-2026-05.md` §8 — bundle structure (legacy naming)
- `deliverables/RTFO-310125/README.md` — current bundle convention (canonical)
- `docs/blueprint-activities.md` §E1 stories S1.1-S1.18

---

## §0 — Structural discrepancy resolved

**Finding:** Action plan §8 uses `04_feedstock_provider_authorisations/` as top-level folder; bundle README uses `04_compliance/` with subdirs `iscc_eu_certificate/` + `rtfo_pathway_declaration/`. Agent S1.14 followed action plan §8 and created a 7th top-level `04_*` folder which collides with `04_compliance/`.

**Resolution:** README is canonical (lives next to bundle, last edited 2026-05-15). The S1.14 output (`04_feedstock_provider_authorisations/`) stays as **separate sibling** dir until Day 6 freeze. Day 5 fix #1: collapse `04_feedstock_provider_authorisations/` into `04_compliance/feedstock_provider_authorisations/` to align with README scheme, OR rewrite README §38 layout to add it as a 7th top-level dir. Decision needed Day 5 morning.

**Owner:** team ingest (5 min decision); document in README v1.

---

## §1 — File presence checklist (against §8 spec, mapped to bundle scheme)

Legend: ✅ present + valid SHA · 🟡 present as placeholder/honest gap · ❌ missing · ⚠ present but needs FINAL

| §8 expected file | Bundle location | Status | Hash side-car | Notes |
|---|---|---|---|---|
| `00_cover_letter.pdf` | `00_cover_letter/00_cover_letter_v0.pdf` | ⚠ v0 only | ✅ | FINAL Day 6 — S1.12 T4 |
| `01_supply_chain_diagram.pdf` | `04_compliance/01_supply_chain_diagram.pdf` | ✅ | ✅ | OK (24 KB, generated 2026-05-15) |
| `02_mass_balance_january_2025.pdf` | `01_annex_a_mass_balance/02_mass_balance_january_2025_v2_endpoint.pdf` | ⚠ v2 only | ✅ | FINAL Day 6 — S1.17 T3 (Annex A regenerate after audit) |
| `03_iscc_pos_chain/` (folder, 4 PoS PDFs) | `03_supplier_evidence/` | ❌ | n/a | The §8 chain folder is **not** what S1.13 produced. S1.13 = STATUS doc, not chain. Chain folder content (per-CP PoS PDFs) is **NOT present** — retroactive PoS requests still pending response. Gap honestly declared in S1.13 PDF + cover letter Outstanding Items. |
| `03_iscc_pos_status.pdf` (S1.13 addition) | `03_supplier_evidence/03_iscc_pos_status.pdf` | ✅ | ✅ | 1.46 MB, 5pp, SHA `d8d06716…`. Documents Pending status per AC. |
| `04_feedstock_provider_authorisations/` | top-level dir (collision flagged §0) | 🟡 | ✅ all 4 | 3 placeholders + `_status_legalisation.pdf`. Real ANLA copies pending OisteBio receipt (ETA 2026-05-27). |
| `05_production_conversion_logs_january_2025.pdf` | — | ❌ | n/a | **Gap — must produce Day 5.** S1.10 owner. kg → litres production log for Jan 2025. |
| `06_audit_trail_export_january_2025.csv` | `05_audit_trail/` | ❌ | n/a | **Gap — must produce Day 5.** S1.9 owner. CSV from `audit_log` table for Jan 2025 writes. |
| `07_stock_carryover_explanation.pdf` (Annex D 339.865 kg) | — | ❌ | n/a | **Gap — must produce Day 5.** S1.8 owner. Annex D explanation; the underlying PDF exists at `templates/reports/stock_carryover.html` per agent-107 reuse — render script may exist. |
| `08_independent_audit_letter.pdf` (optional) | — | ❌ | n/a | Optional per §8. Skip if no ISCC certifier engaged. Current state: no certifier formally engaged → omit + document in evidence index. |
| `09_evidence_index.pdf` | `09_evidence_index_v0.pdf` | ⚠ v0 only | ✅ | FINAL Day 6 — S1.17 T4 (cross-reference Annex A FINAL hash + status of 03_iscc_pos_chain gap + Annex D hash + cover letter hash). |

---

## §2 — Bundle README structural items

| Item | Status | Notes |
|---|---|---|
| README.md present + current | ✅ | Last edit 2026-05-15; mentions deadline "21-22 May 2026". |
| `MANIFEST.sha256` populated | ❌ | **Header only**, no checksum lines yet. Must regenerate Day 6 after Annex A FINAL + cover letter FINAL + evidence index FINAL. |
| DB snapshots (S1.16) | ✅ | 4 snapshots present in `05_audit_trail/db_snapshots/`: 2026-05-15 + pre_0009 + pre_0010 + pre_0011 (all 2026-05-20). Day 6 FINAL snapshot still to take post Annex A FINAL. |

---

## §3 — Day 5/Day 6 action list (gaps + finals)

Ordered by criticality + dependency:

1. **GAP — production conversion log Jan 2025 (S1.10)** [Day 5]
   - Output: `05_production_conversion_logs_january_2025.pdf`
   - Source: `daily_production` table for Jan 2025; columns kg_input → kg_processed → litres_eu / litres_plus.
   - Owner: team ingest. Reuse `pdf_renderer` service.

2. **GAP — audit trail CSV Jan 2025 (S1.9)** [Day 5]
   - Output: `05_audit_trail/06_audit_trail_export_january_2025.csv`
   - Source: `audit_log` table, filter `entity_date >= '2025-01-01' AND entity_date <= '2025-01-31'` (or by `created_at` Jan 2025 if more appropriate).
   - Owner: team ingest. Likely a simple psql `COPY (SELECT...) TO STDOUT WITH CSV HEADER` one-liner.

3. **GAP — Annex D stock carry-over Jan 2025 (S1.8)** [Day 5]
   - Output: `07_stock_carryover_explanation.pdf` (location: probably new top-level `06_annex_d/` or as sibling to Annex A).
   - Source: 17 K-only rows from JANUARY2025 sheet representing 339.865 kg end-Jan stock movement.
   - Template `templates/reports/stock_carryover.html` exists (referenced by agent-107 as CSS source). Render script may exist as `scripts/render_stock_carryover_sample.py`.

4. **STRUCTURAL — resolve `04_*` directory collision** [Day 5 AM]
   - Either rename `04_feedstock_provider_authorisations/` → `04_compliance/feedstock_provider_authorisations/`, OR add it to README as 7th top-level dir.
   - Owner: team ingest, 5-minute decision + commit.

5. **FINAL — Annex A v3 FINAL (S1.17)** [Day 6]
   - Output: `01_annex_a_mass_balance/02_mass_balance_january_2025_FINAL.pdf`
   - Regenerate post pre-audit walkthrough. New SHA-256 listed in evidence index + cover letter manifest.

6. **FINAL — Cover letter v2 (S1.12 T4)** [Day 6]
   - Output: `00_cover_letter/00_cover_letter_FINAL.pdf`
   - Must cite Annex A FINAL hash + Annex D hash + iscc_pos_status hash + manifest hash.

7. **FINAL — Evidence index v1 (S1.17 T4)** [Day 6]
   - Output: `09_evidence_index_FINAL.pdf`
   - Cross-reference docs ↔ DfT rejection points. Includes hash of every other file.

8. **FINAL — MANIFEST.sha256 regen** [Day 6 EOD]
   - Run command from README §83.
   - Verify all lines `OK` via `sha256sum -c`.

9. **FINAL — DB snapshot Day 6** [Day 6 EOD]
   - `db_snapshot_2026-05-20_final.sql.gz` + `.sha256`
   - Capture state immediately before bundle freeze.

---

## §4 — Risk register at Day 4 (carried to Day 5/6)

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | 03_iscc_pos_chain remains empty at Day 7 (certifier non-response) | HIGH | S1.13 status PDF declares Pending openly; cover letter Outstanding Items + 30-day post-acceptance commitment frame this as known gap not a defect. |
| R2 | ANLA permits not received from OisteBio by Day 6 | MEDIUM | Placeholders submitted with explicit "awaiting receipt" banners + 4-8 week consular legalization timeline. Status PDF documents ETA. |
| R3 | Production log conversion (kg → litres) not derivable for Jan 2025 if `litres` column null | MEDIUM | Check `daily_production` schema Day 5 AM. If null, S1.1 decision D2 implies derived value column or MV — confirm with action plan §4 Week 1. |
| R4 | Annex D `stock_carryover` template not configured for 339.865 kg Jan-specific narrative | LOW | Template + render script already present per agent-107 reference. Just need invocation with Jan 2025 data + 17 K-only row IDs. |

---

## §5 — Pre-audit sign-off

| Role | Name | Sign-off |
|---|---|---|
| Team ingest (digital) | DFT digital agent | ✅ Walk-through executed 2026-05-20 |
| OisteBio (compliance) | TBC | ⏳ Day 5 review needed |
| Crown Oil (legal) | TBC | ⏳ Day 5 review needed |

**Outcome:** Bundle currently 4/10 §8 files complete + 2/10 placeholder + 4/10 missing. Day 5 critical path: render 3 missing PDFs (production log, audit CSV, Annex D). Day 6 finalize Annex A + cover letter + evidence index + manifest + final DB snapshot. Day 7 ROS upload + DfT notification (S1.18).

**Recommendation to orchestrator:** sequential render of remaining 3 gap PDFs can be parallelized via 3 sub-agents (similar approach to Day 1-3 parallel work). Each render task is small (template + Jinja + WeasyPrint via existing `pdf_renderer`).
