# DfT Audit Evidence Matrix — Consignment `c-1` (DEL-CRW-2025-2)

**Subject**: `/app/logistics/1` — c-1 = `DEL-CRW-2025-2`, off_taker Crown Oil Ltd (UK),
product DEV-P100, total 576,270 kg, Q3 2025 (prod 1 Jun → 31 Aug 2025), status `at_utb`.

**Source verifications** (executed 2026-05-26):

- DB live query on `dft-project_db_1` (PostgreSQL 16, schema `public`)
- Playwright headless render of `/app/logistics/1`
  (snapshot `/tmp/audit_c1_dom.txt`, `/tmp/audit_c1_screenshot.png`,
  `/tmp/audit_c1_report.json`)
- Source: `landing/src/app/app/logistics/[id]/page.tsx` (557 lines),
  `landing/src/components/chain-of-custody/ChainOfCustodySummary.tsx` (301 lines)

---

## 1. UK / DfT regulatory framing

### 1.1 RTFO feedstock eligibility

Per UK GOV "Renewable transport fuel obligation (RTFO) — list of fuels and
feedstocks", row applicable here is:

> **Renewable component of end-of-life tyres**
> — natural rubber portion of end-of-life tyres (ELT)
> — accepted from **15 March 2013**
> — **Fuel Measurement & Sampling (FMS)** required to prove renewable share
> — **Double counting** (2× RTFC per litre/kg of renewable fuel produced)

### 1.2 Chain-of-custody — Deeba Rehman letter (UK DfT Low Carbon Fuels)

Eight per-batch evidence requirements (deadline 22-May-2026, recipient is
Crown Oil — they package and submit; OisteBio supplies bundle):

| # | Verbatim ask |
|---|---|
| 1 | Feedstock providers ISCC-registered to handle **tyres** at the time of each exchange |
| 2 | Feedstock delivery notes per batch |
| 3 | Each delivery recorded into the mass balance |
| 4 | Full traceability input → processing → output |
| 5 | Reconciliation feedstock kg ↔ finished fuel **litres** + **conversion rate** |
| 6 | Mass balance records of fossil byproduct sold onwards |
| 7 | Each batch delivered to UK — BL, transport, port, customs |
| 8 | Invoices producer ↔ Crown Oil |

---

## 2. State of `/app/logistics/1` — render captured

### 2.1 Header (rendered)

| Field | Value |
|---|---|
| Title | `DEL-CRW-2025-2` |
| Off-taker · grade | Crown Oil Ltd · DEV-P100 |
| Status pill | `AT UTB` |
| EAD pill | `EAD 20/20 FILED` |
| Total kg | 576,270 |
| Prod from | 1 Jun 2025 |
| Prod to | 31 Aug 2025 |
| Legs / units | 4 / 29 |

### 2.2 ChainOfCustodySummary — six stages (rendered)

| Stage | Primary line | Secondary line | Drill-down available? |
|---|---|---|---|
| Upstream (ELT feedstock) | `572 eRSV · 6 suppliers` | `10,083,985 kg input · 1 Jun 2025 → 31 Aug 2025` | ❌ no `details.upstream` passed by page.tsx |
| Production (Girardot CO) | `74 days · 3,014,511.546 kg plant total` | `Yield 29.9 % · allocated to consignment 576,270 kg (74 days)` | ✅ `productionDetail` (prod_date + kg_allocated) |
| Inland (Girardot → Cartagena) | `29 containers · 29 inland eRSV` | `576,270 kg net · GIR/25/08-06/01 … GIR/25/10-07/14` | ✅ `inlandDetail` table (29 rows + Render PDF chip per shipment) |
| Ocean BL (Cartagena → Rotterdam) | `2 BL` | `CMDU856254189, CMDU877254433` | ✅ `oceanDetail` = ChainTimeline (4 legs) |
| UTB transload (Rotterdam) | `Stock residual 75,860 kg` | — | ❌ no `details.utb` passed |
| Outbound (PoS → Crown Oil UK) | `20 PoS · 500,410 kg delivered` | `OISCRO-0013-25 … OISCRO-0032-25 · eRSV out 1/20` | ✅ `outboundDetail` (20 rows + EAD PDF chip + Invoice PDF chip) |

### 2.3 Top-strip chips (rendered)

- `link balanced` (production_link_kg 576,270 = consignment_kg 576,270 ✅)
- `eRSV out 1/20` — **OISCRO-0013-25** has `ersv_outbound_no = CO/25/007` (the
  other 19 are NULL). Corrected 2026-05-26 — earlier matrix draft misidentified
  this row as OISCRO-0021-25.

### 2.4 Notes (rendered)

> Backfill from BL CMDU856254189 + CMDU877254433 (Cartagena → Rotterdam) + UTB BV transload + 20 ISO tanks to Crown Oil Bury UK. Reconciled 2026-05-23. See /tmp/bl_dl/RECONCILIATION.md.

### 2.5 Console / network health

- 0 page errors, 0 failed API requests
- 1 console warning (Radix `aria-controls` SSR/CSR hydration mismatch, benign)

---

## 3. Evidence matrix — 8 DfT points × current state

Legend severity: 🔴 critical · 🟡 medium · 🟢 cosmetic · ✅ already covered

### Point 1 — Feedstock providers ISCC-registered for tyres at time

**DfT asks**: per supplier, prove they held a valid ISCC certificate whose
scope covers end-of-life tyres at the time of every exchange in the window
1 Jun 2025 → 31 Aug 2025.

**Have in DB** (verified 2026-05-26 — counts are Q3 daily_inputs rows, not days):

| supplier | code | rows_Q3 | rows_with_cert | distinct_certs_used | cert (where linked) |
|---|---|---|---|---|---|
| KAL TIRE | KALTIRE | 161 | 161 | 1 | `US201-138762025` (2025-05-18 → 2026-05-17) ✅ |
| EFFICIEN TECHNOLOGY | EFFICIEN | 168 | 168 | 1 | `US201-158772025` (2025-01-26 → 2026-01-25) ✅ |
| ≤5 TON | LE5TON | **309** | **0** | **0** | 🔴 **NO cert linked on any Q3 row.** `supplier_certificates` table binds `CO222-00000026` etc. to LE5TON but `daily_inputs.certificate_id IS NULL` for all 309 rows. Ingest did not propagate. |
| PYRCOM SAS | PYRCOM | 131 | 131 | 1 | `ES216-20249051` (2024-10-17 → 2025-10-16) ✅ |
| BOLDER INDUSTRIES | BOLDER | 70 | 70 | 1 | `US201-120372025` (2025-04-04 → 2026-04-03) ✅ |
| ESENTTIA | ESENTTIA | 40 | 40 | 1 | `CO222-00000027` (2024-10-17 → 2025-10-16) ✅ |

**Have on page**: only `6 suppliers` count text. No cert numbers, no scope
text, no PDF links scoped to this consignment.

**Gap**: 🔴 **CRITICAL** — page must surface a "Feedstock ISCC coverage"
table for the 6 suppliers active in c-1, listing cert_number, scheme,
valid_from/to, PDF chip, AND a parsed `scope.material_groups` field (does
the certificate scope actually include tyres / end-of-life tyres?). DB has
no `scope_material_groups` column today → migration + manual ingest from
ISCC PDF needed.

### Point 2 — Feedstock delivery notes per batch

**DfT asks**: per inbound load, a supplier delivery note (DDT / waybill /
ISCC sustainability declaration) tying the load to a sustainability claim.

**Have in DB** (verified):

- `daily_inputs.ersv_number` (text) — intra-OisteBio eRSV (Colombia)
- `daily_inputs.certificate_id` (FK) — links to supplier ISCC cert
- **NO** `delivery_note_no` column
- **NO** `supplier_ddt_ref` column

**Have on page**: only the count `572 eRSV` in Upstream summary; the
underlying 572 rows are NOT drilled down on c-1 page (no `details.upstream`
passed).

**Gap**: 🔴 **CRITICAL** —
(a) DB schema gap: add `daily_inputs.supplier_ddt_no` + `_pdf_ref` columns
(b) UI gap: pass `details.upstream` to `ChainOfCustodySummary`, render
table of inbound eRSVs scoped to the consignment's prod-date window with
supplier + cert + DDT PDF chip
(c) Cliente must supply DDT PDFs (likely backlog)

### Point 3 — Each delivery recorded into the mass balance

**DfT asks**: every inbound load appears in mass balance ledger with kg
and certification status.

**Have in DB** (verified):

- 572 daily_inputs rows in the Q3 window across the 6 suppliers
- `mass_balance_ledger` table present
- `v_chain_summary.inbound_feedstock_kg = 10,083,985` ✅

**Have on page**: summary line `572 eRSV · 6 suppliers · 10,083,985 kg`.

**Gap**: 🟡 **MEDIUM** — counts are correct but no drill-down (same
upstream details gap as #2). Once `details.upstream` is wired this point
is fully covered for evidence purposes.

### Point 4 — Full traceability input → processing → output

**Have in DB**: `consignment_production_link` (74 days, 576,270 kg
allocated = consignment_kg exactly), `shipment_leg` (4 legs sequenced),
`consignment_pos` (20 PoS), `consignment_pos_customs` (20 EAD).

**Have on page**: full ChainOfCustodySummary widget visible end-to-end +
`link balanced` chip green.

**Gap**: ✅ **NONE** for traceability per se. (Composite of #1-#8.)

### Point 5 — Reconciliation feedstock kg ↔ finished fuel litres + conversion rate

**DfT asks**: prove the kg-to-litre conversion factor used to convert the
plant's mass output into RTFC-eligible volume.

**Have in DB** (verified):

- `daily_production.litres_eu`, `litres_plus` populated (Q3 totals:
  3,898,737 L EU + 4,704,635 L PLUS)
- `product_densities` table populated for Jun/Jul/Aug 2025:
  EU 0.770 / 0.774 / 0.775 kg/L (source: "OisteBio process owner
  2026-05-21")
- Conversion rate visible: yield 29.9 % = `3,014,511 / 10,083,985`

**Have on page**: `Yield 29.9 %` rendered in Production secondary line.

**Gap**: 🟡 **MEDIUM** — page shows yield_mass (kg/kg) but does **not**
show:
(a) consignment_kg → consignment_litres via period-weighted density
(consignment 576,270 kg → ~744,219 L EU @ blended density)
(b) per-month density table (audit-ready, footnoted with source +
effective_from)
(c) FMS reference (point 1 of RTFO eligibility requires Fuel Measurement &
Sampling — neither the page nor the DB references the FMS protocol used to
prove the renewable share of ELT-derived oil)

### Point 6 — Mass balance records of fossil element sold onwards

**DfT asks**: prove that the non-renewable byproduct (Plus oil, syngas,
carbon black, metal scrap) is independently tracked and that no
double-counting occurs (the fossil share is sold without a renewable
claim).

**Have in DB** (verified):

- `daily_production` has byproduct columns populated:
  carbon_black 1,388,950 kg, metal_scrap 849,843 kg, h2o 153,695 kg,
  gas_syngas 429,442 kg, losses 194,379 kg, plus_prod 4,053,165 kg
- `byproduct_sale` table exists; **58 rows total, 0 active, 58 soft-deleted**
  (all test data created 2026-05-24 → 2026-05-25, then voided). No production
  data has ever been ingested.
- `byproduct_buyer` table exists

**Have on page**: zero mention of byproduct on c-1.

**Gap**: 🔴 **CRITICAL** —
(a) DB data gap: `byproduct_sale` empty — no fossil-sale invoice trail
exists in production. Cliente must supply sales records for plus_oil /
carbon_black / metal_scrap for the c-1 window. (Per memory:
`feedback_backfill_after_migration` — schema ≠ data; was flagged
2026-05-24 but never backfilled.)
(b) UI gap: c-1 page has no byproduct row in the chain summary. Either
add a 7th stage to ChainOfCustodySummary ("Byproduct" — kg produced vs kg
sold + invoice link) or surface a sibling card below the chain.

### Point 7 — Each batch delivered to UK (BL, transport, port, customs)

**Have in DB** (verified):

- 4 shipment_leg rows: 2 BL ocean (CMDU856254189 Jun 11, CMDU877254433
  Jul 3), 1 utb_transload (UTB-2025-Q3-CONSOLIDATED Jul 20), 1
  delivery_uk (commercial_invoice JLY001-JLY020 Aug 15)
- 20 EAD MRN rows under `consignment_pos_customs` with customs_office
  populated

**Have on page**: ocean leg drill-down via ChainTimeline (with leg seq,
document type, refs), EAD chip + PDF per PoS, transload leg, delivery_uk
leg.

**Gap**: ✅ **NONE** at structural level. Open verifications:
- Are the BL PDFs actually stored (`pdf_ref` populated) so chips open?
  → check needed
- Transload report `UTB-2025-Q3-CONSOLIDATED` — is the actual PDF on
  disk? Audit will demand it
- `JLY001-JLY020` delivery commercial_invoice — 20 docs implied; only
  one row in shipment_leg

### Point 8 — Invoices producer ↔ Crown Oil

**Have in DB** (verified): 20 rows in `consignment_pos_customs` with
`invoice_no` and `invoice_pdf_ref`:
- OISCRO-0013-25: `invoice_no = NULL`, `invoice_pdf_ref =
  c-1/INV_OIS-INV250023.pdf` 🟢 minor data hygiene
- OISCRO-0014-25 … OISCRO-0032-25: all 19 with `invoice_no =
  OIS-INV250024…OIS-INV250042` and matching PDF ref

**Have on page**: 20 Invoice chips (one per PoS row), each opening the
invoice modal. OISCRO-0013-25 chip uses filename-derivation fallback
(E8-F2 fix).

**Gap**: 🟢 minor — write a single `UPDATE consignment_pos_customs SET
invoice_no = 'OIS-INV250023' WHERE consignment_id=1 AND
pos_number='OISCRO-0013-25';` so the DB matches the filename and the
fallback is no longer needed.

---

## 4. Summary — work to reach "inoppugnabile"

### 4.1 Critical (audit failure if missing)

| Gap | Action | Owner |
|---|---|---|
| Cert ISCC scope coverage for tyres (point 1) | Add `certificates.scope_material_groups` text column + ingest from ISCC PDFs + render on c-1 page in new "ISCC coverage" section | Dev + cliente (PDF read) |
| Inbound DDT per batch (point 2) | Add `daily_inputs.supplier_ddt_no/_pdf_ref` cols + UI upstream drill-down + backfill DDT files | Dev + cliente |
| Byproduct sales empty (point 6) | Backfill `byproduct_sale` from cliente books + render 7th chain row | Dev + cliente |

### 4.2 Medium

| Gap | Action |
|---|---|
| Upstream drill-down missing | Wire `details.upstream` in `page.tsx` — pass inbound_ersv list table |
| Reconciliation kg→L not rendered | Add "Volume reconciliation" sub-card: consignment_kg → consignment_litres via period-weighted density, with FMS protocol reference |
| UTB drill-down missing | Wire `details.utb` — show transload report metadata + PDF chip |

### 4.3 Cosmetic / data hygiene

| Gap | Action |
|---|---|
| OISCRO-0013-25 invoice_no NULL | UPDATE single row in DB |
| Production drill-down has no link to daily inputs | Make `prod_date` cell in `productionDetail` a `<Link>` to `/app/inputs?date_from=X&date_to=X` |

### 4.4 Already inoppugnabile

- Point 4 traceability (overall structure)
- Point 7 UK delivery (BL/transload/EAD/delivery_uk all present)
- Point 8 invoices (20/20 with PDF chips, modulo the one DB hygiene fix)

---

## 5. Red-team pass — pending

Pass this matrix through a "DfT auditor" persona (single serial subagent in
main thread; no isolation / no legions) for adversarial challenge of every
"✅" and every "🟢" claim. Iterate until red-team produces no actionable
new gaps.

Output of red-team round 1 will be appended in §6 with date stamp.

---

## 6. Red-team round 1 (DfT auditor pass · 2026-05-26)

**Auditor**: Deeba Rehman, Senior Compliance Officer, UK DfT Low Carbon Fuels.
**Method**: live read against `dft-project_db_1` (PostgreSQL 16) + render at
`/app/logistics/1` + matrix §1-§5 + reconciliation note
`/tmp/bl_dl/RECONCILIATION.md`.
**Verdict at consignment level**: **REJECT, bundle not fit for ROS submission.**
Multiple categorical failures across points 1, 2, 5, 6, 7. Re-submission required.

### 6.0 Top-line failure modes (any one kills the bundle)

| # | Failure | Where it sits |
|---|---|---|
| F0-A | **LE5TON: 309 inbound rows, 0 certificate_id, 307/309 missing eRSV, contract is `SD` placeholder** | point 1, 2 |
| F0-B | **FMS / C14 protocol nearly absent**: 879 Q3 input rows → 0 with `c14_value`, 41/879 (4.7 %) with `c14_analysis`, 61/879 (6.9 %) with `manuf_veg_pct` | point 1 (RTFO eligibility), point 5 |
| F0-C | **BL2 (CMDU877254433) dated 2025-07-03 but all 14 containers loaded 2025-07-10** — BL pre-dates cargo by 7 days. Invalid per Hague-Visby Art. III(3) | point 7 |
| F0-D | **Zero active `byproduct_sale` rows** (58 exist, all soft-deleted test data from 2026-05-24) — no fossil-fraction sales ledger, no proof of non-double-counting against syngas energy claim | point 6 |
| F0-E | **No ISCC certificate PDFs**: all 7 active certs in scope have `pdf_ref = NULL` and `document_url = NULL` | point 1 |
| F0-F | **No scope field**: `certificates` table has no `scope_material_groups` column. Cannot prove cert covers "end-of-life tyres" vs "rubber waste" vs "mixed plastic" | point 1 |
| F0-G | **20/20 PoS carry identical GHG figures** (`ghg_total = 16.95`, `ghg_saving_pct = 81.96`). Statistically impossible across 6 suppliers × 74 days × 2 batches × 3 months. Indicates hard-coded default, not per-batch calc | point 4, point 5 |

Any one triggers full bundle rejection under ISCC EU 203 §2.4 (system integrity)
and RTFO Order Art. 4(2)(b).

### 6.1 Point-by-point verdicts

| Point | Matrix v1 | Red-team |
|---|---|---|
| 1 — ISCC cert tyres | 🔴 | **REJECT** — worse than matrix (no PDFs, no scope, LE5TON unlinked) |
| 2 — DDT fornitore | 🔴 | **REJECT** — confirmed |
| 3 — Each delivery in MB | 🟡 | **COND-ACCEPT** for 5 cert-linked suppliers; **REJECT** for LE5TON's 309 rows |
| 4 — Traceability | ✅ | **REJECT** — allocation methodology undocumented; no soft-delete on `consignment_production_link`; cross-consignment double-claim cannot be ruled out from schema |
| 5 — kg↔L + conversion | 🟡 | **REJECT** — FMS gap fatal under RTFO ELT eligibility row |
| 6 — Byproduct sold onwards | 🔴 | **REJECT** — confirmed; syngas energy claim cross-check missing |
| 7 — UK delivery | ✅ | **REJECT** — BL2 pre-dating + 0/29 inland transporter/driver/plate + 6 containers reused 2-3× + gross_kg 1/20 + UTB consolidated (no per-tank) + BL1 tare arithmetic inconsistent + PoS/Customs 3 kg delta |
| 8 — Invoices | ✅ | **COND-ACCEPT** — PDFs exist; Colombian DIAN cross-ref needed; covers 500,410/576,270 kg (residual correctly excluded) |

### 6.2 §2.2 widget — auditor navigability

**Insufficient for audit**, navigable for sales demo. Specific gaps:

1. Upstream row no drill-down — auditor cannot expand 572 eRSV × 6 suppliers
2. UTB row no drill-down — residual 75,860 kg fate hidden
3. No row for byproduct fate (carbon black, plus oil, metal, syngas)
4. No row for FMS / C14 / biogenic fraction
5. "ERSV OUT 1/20" chip mislabels which PoS is populated (matrix says 0021, DB says 0013)
6. "LINK BALANCED" chip only checks scalar equality, not allocation integrity across consignments

### 6.3 §4 "already inoppugnabile" claims — challenged

| Matrix v1 claim | Red-team |
|---|---|
| Point 4 traceability ✅ | **REJECTED** (allocation methodology + soft-delete gap) |
| Point 7 UK delivery ✅ | **REJECTED** (7 sub-failures listed in 6.1) |
| Point 8 invoices ✅ | **COND-ACCEPTED** (PDFs + DIAN cross-ref pending) |

### 6.4 Cross-cutting concerns surfaced

| # | Concern | Severity |
|---|---|---|
| X1 | No sustainable/non-sustainable segregation in 10,083,985 kg → yield 29.9 % computed on un-segregated total | 🔴 |
| X2 | GHG uniformity (X.95 / 81.96 across 20 PoS) — per-PoS Annex V Part C calc absent | 🔴 |
| X3 | ISCC scope strings unverified ("end-of-life tyres" vs "rubber waste" vs "mixed plastic" all map to different RTFO rows) | 🔴 |
| X4 | `/tmp/bl_dl/RECONCILIATION.md` — no signature, no version control, volatile path | 🟡 |
| X5 | No `weighbridge_ticket_no` column on `daily_inputs` or `shipment_leg` | 🟡 |
| X6 | 75,860 kg UTB residual — no carried-balance statement to Q4 OisteBio mass balance | 🟡 |
| X7 | Header should render 576,270 = 500,410 delivered + 75,860 residual explicitly | 🟢 |
| X8 | 19/20 PoS missing outbound eRSV (not just cosmetic — chain-of-custody handover evidence per ISCC EU 203 §4.2) | 🔴 |

### 6.5 Errors in matrix v1 caught by red-team

1. Matrix §3 Point 1 LE5TON table row claims "CO222-00000026 (Q3) + 3 placeholder + ES216-20254036" → reality: **0/309 daily_inputs Q3 rows have certificate_id populated for LE5TON.** The `supplier_certificates` binding is decorative; ingest did not propagate.
2. Matrix §2.3 says outbound eRSV populated on OISCRO-0021-25 → reality: **OISCRO-0013-25 carries `CO/25/007`.** Misidentified row.
3. Matrix §3 Point 6 says `byproduct_sale` is "empty (zero rows)" → reality: **58 rows exist, all soft-deleted test data from 2026-05-24.** User-facing claim correct (active=0); DB-state description was misleading.

### 6.6 Mandatory remediation before re-submission (ordered)

1. **F0-A LE5TON**: produce ISCC cert + DDT + eRSV for all 309 Q3 rows, OR re-classify 1,226,479 kg as non-sustainable and recompute claimable share
2. **F0-B FMS / C14**: produce FMS protocol document + at minimum monthly C14 results for Q3 window (4.7 % coverage will not pass)
3. **F0-C BL2 pre-dating**: written explanation from CMA-CGM + OisteBio shipping for 7-day BL/load discrepancy
4. **F0-D Byproduct sales**: backfill `byproduct_sale` with real Q3 2025 invoices; prove syngas burnt-for-power not double-claimed
5. **F0-E ISCC cert PDFs**: attach PDF + ISCC registry screenshot per cert per quarter
6. **F0-F Scope text**: parse cert scope strings; downgrade RTFC eligibility if any cert is "rubber waste" or broader
7. **F0-G Per-PoS GHG**: recompute under RED II Annex V Part C; identical figures will be challenged
8. Populate `transporter/driver/vehicle_plate` on all 29 inland; produce weighbridge tickets
9. UTB per-tank transload paper (20 outbound tanks)
10. Reconcile 3 kg PoS/Customs delta on OISCRO-0024-25 — single source of truth
11. Produce or explain 19 missing outbound eRSV
12. Re-issue reconciliation memo signed, dated, versioned, out of /tmp

**Re-audit window**: 14 calendar days from remediation pack receipt.

**Signed** · Deeba Rehman · Senior Compliance Officer · DfT Low Carbon Fuels · 2026-05-26

---

## 7. Action plan after red-team round 1

Matrix v1 was over-optimistic. Real picture: **7 blocking failure modes, 8
cross-cutting concerns, 3 self-caught matrix errors**. Bundle as-is would be
rejected at first auditor pass.

### 7.1 Hierarchy of remediation effort

| Tier | Items | Type | Time est |
|---|---|---|---|
| **A — Data we own, ship today** | F0-D (backfill `byproduct_sale` if cliente has invoices), F0-E (link ISCC PDFs we already have on disk), §3 P8 invoice_no hygiene, X7 header reconciliation line, matrix errors (3) | DB UPDATE + UI patch | 1-2 days |
| **B — Schema migrations + UI** | F0-F `scope_material_groups` column + parser, §3 P2 `supplier_ddt_no` column + upstream drill-down, §3 P5 volume sub-card, soft-delete on `consignment_production_link`, `weighbridge_ticket_no` columns | migration + ingest + UI | 3-5 days |
| **C — Cliente-dependent** | F0-A LE5TON cert+DDT+eRSV backlog OR re-classify, F0-B FMS protocol + C14 lab results, F0-C BL2 explanation, F0-D actual byproduct sales invoices, F0-G per-PoS GHG calc working paper, F0-E ISCC registry screenshots, X4 signed reconciliation memo | data the cliente owes us | TBD — block on Paolo Ughetti / Hugo (operations) |

### 7.2 Recommended next move

Start tier A immediately while drafting the **cliente data request letter** for
tier C. Tier B follows once tier C arrives — pointless to build UI surface for
fields the cliente cannot populate.

Tier C data request goes to Paolo Ughetti with line-item asks:
- LE5TON: 309 row backlog of cert + DDT + eRSV, or written re-classification
- FMS protocol document + C14 lab results (ASTM D6866) for Q3 2025
- CMA-CGM written explanation for BL2 pre-dating
- Q3 2025 byproduct sales invoices (plus oil, carbon black, metal scrap, syngas energy claim status)
- Per-PoS GHG calc working paper (20 PoS)
- ISCC registry screenshots × 6 suppliers
- Signed reconciliation memo replacing /tmp note

### 7.3 Pipeline forward

1. ✅ Matrix v1
2. ✅ Red-team round 1 → 7 failure modes, 3 matrix errors caught
3. ✅ **Tier A** (2026-05-26): matrix v1.1 sync con DB reale + 7 cert PDF
   linkati a DB + lettera cliente tier C draftata
4. ⏳ Tier C data arrives → tier B schema/UI
5. ⏳ Red-team round 2 against patched bundle
6. ⏳ Iterate until red-team accepts
7. ⏳ Final bundle PDF + cover letter for Crown Oil

---

## 8. Tier A — log azioni 2026-05-26

### 8.1 Matrix v1 → v1.1 (sync con DB reale)

| Errore matrix v1 | Verifica DB | Patch |
|---|---|---|
| "LE5TON ha CO222-00000026 + ES216-20254036" | 309 Q3 rows, **0 con certificate_id** | §3 Point 1 table aggiornata con `rows_with_cert`, LE5TON marcato 🔴 NO cert |
| "Outbound eRSV su OISCRO-0021-25" | DB: OISCRO-**0013**-25 ha `CO/25/007` | §2.3 corretto + nota errore |
| "`byproduct_sale` empty" | 58 rows, 0 active, 58 soft-deleted (test 24-25 maggio 2026) | §3 Point 6 chiarito |

### 8.2 7 cert PDF supplier linkati a DB

PDF copiati da `deliverables/RTFO-310825/03_supplier_evidence/certificates/`
a `data/certificates/supplier-q3/` (bind-mount `/data/certificates:ro` nel
container backend). Verificato endpoint `GET /certificates/{id}/pdf` →
HTTP 200, application/pdf, 220 KB (test cert id=14 KAL TIRE).

| cert_number | PDF reale (intestazione) | pdf_ref linkato |
|---|---|---|
| US201-138762025 | KAL TIRE | `supplier-q3/US201-138762025_KALTIRE.pdf` ✅ |
| US201-158772025 | EFFICIEN TECHNOLOGY | `supplier-q3/US201-158772025_EFFICIEN.pdf` ✅ |
| CO222-00000027 | ESENTTIA | `supplier-q3/CO222-00000027_ESENTTIA.pdf` ✅ |
| ES216-20249051 | PYRCOM | `supplier-q3/ES216-20249051_PYRCOM.pdf` ✅ |
| US201-120372025 | BOLDER | `supplier-q3/US201-120372025_BOLDER.pdf` ✅ |
| CO222-00000026 | **LITOPLAS** ⚠️ | `supplier-q3/CO222-00000026_LITOPLAS.pdf` ⚠️ binding LE5TON+ESENTTIA mis-attribuito |
| ES216-20254036 | **CI ECOGRAS COLOMBIA** ⚠️ | `supplier-q3/ES216-20254036_ECOGRAS.pdf` ⚠️ binding LE5TON+LITOPLAS mis-attribuito |

**Scoperta nuova non in red-team round 1**: due cert PDF (CO222-00000026,
ES216-20254036) hanno intestazione LITOPLAS / ECOGRAS rispettivamente ma
sono bind-attribuiti a LE5TON / ESENTTIA / LITOPLAS in `supplier_
certificates`. La memoria `project_cert_correction_0010` accenna al
problema PYRCOM ma non a questi due. Documentato in lettera cliente
(richiesta 7).

### 8.3 Lettera cliente tier C draftata

File: `docs/audit-dft-c1-cliente-data-request.md` — 13 richieste a Paolo
Ughetti, ordinate per criticità audit (5 BLOCCANTI 🔴 + 8 MIGLIORATIVE 🟡).
Da inviare via email separata.

### 8.4 Cosa NON è stato fatto in tier A (consapevolmente)

- **Non** rimosso il binding mis-attribuito LITOPLAS↔LE5TON,
  LITOPLAS↔ESENTTIA, LE5TON↔ES216-20254036. Audit history
  → richiede migration 0020 cert-correction-round-2 con soft-deprecate
  (rispetto memoria `project_iscc_audit_safety`)
- **Non** ricompilato/restart backend — UPDATE è data-only, route è già
  registrata e testata
- **Non** modificata UI `/app/logistics/1` per esporre cert chip — quello
  è tier B (post arrivo dati cliente)
- **Non** deploy su Hetzner — solo locale, come da `feedback_local_first_
  always`

End §7.
