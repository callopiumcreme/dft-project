# RTFO Gap Analysis — DFT Project vs UK RTFO Requirements

> Date: 2026-05-12 (rev. 2026-05-15)
> Source DFT: `BLUEPRINT.md` + `backend/app/models/` + 5 alembic migrations (0001 schema, 0002 seed, 0003 mvs, 0004 drop stock markers, 0005 product_densities)
> Source RTFO: `docs/rtfo-essential-guide.md` (DfT essential guide, fetched 2026-05-12)
> Plant: Girardot (Colombia) — pyrolysis of **ELT (end-of-life tyres)** → DEV-P100 refined pyrolysis oil + carbon black + metal scrap + H₂O + syngas + losses
> Confirmed off-taker: **Crown Oil UK** (single project buyer, Europe excluded)
> Current certification scheme tracked: **ISCC EU only** (`Certificate.scheme` defaults `"ISCC EU"`)
> Cross-ref: `docs/dft-action-plan-2026-05.md`, `docs/dft-5wd-activity-plan.md`

---

## 0. Executive summary

The DFT system today is an **input/output mass-balance tracker** designed around **ISCC EU** voluntary-scheme bookkeeping. It records daily feedstock inputs (car/truck/special kg), pyrolysis outputs (EU prod / plus prod / carbon black / metal scrap / H2O / syngas / losses), supplier certificates and contracts, plus C14 bio-share fields on inputs.

The UK **RTFO** is a parallel obligation regime that issues tradeable **RTFCs** per litre of sustainable renewable fuel *supplied into UK transport*, with a separate **dRTFC** track for **Development Fuels** (RFNBO, RCF, double-counting wastes) carrying a 1.619% sub-target on top of the 14.054% main obligation (2025 values).

For the Girardot plant to participate in RTFO via **Crown Oil UK** (already identified as DEV-P100 buyer), the DFT system needs additions in **six areas**: (1) GHG carbon-intensity per batch, (2) feedstock classification per the RTFO list, (3) RTFC inventory, (4) ROS-shaped reporting export, (5) carry-over + buy-out ledger, (6) verifier workflow. None of these exist today. The mass-balance core, supplier/certificate registry, and audit log already in place are reusable foundations — they do not need to be replaced, only extended.

Crucially: **feedstock = ELT (end-of-life tyres) → pyrolysis output is classified as Recycled Carbon Fuel (RCF) under RTFO**, earning **1 dRTFC per litre** (no biogenic double-count) and using the **Annex D counterfactual GHG methodology** — fundamentally different from ISCC EU's biogenic-content + lifecycle approach. ELT is 100% fossil-origin material (synthetic rubber), so there is no biogenic share to split: the entire DEV-P100 stream sits on the RCF path. This shapes most of the recommendations below.

---

## 1. Regulatory context

| | DFT today | RTFO |
|---|---|---|
| Scheme | ISCC EU (voluntary, EU RED II) | UK RTFO (statutory obligation) |
| Unit of accounting | kg of feedstock + kg of product | litres (or kg-equiv with multipliers) of fuel *supplied* in UK transport |
| Trigger | Continuous mass-balance bookkeeping | Supplier ≥ 450,000 L/yr of relevant fuel in UK |
| Evidence | Sustainability declarations + ISCC audit | RTFC awards via ROS + independent verifier + targeted DfT checks |
| Compliance object | Bio-share / GHG saving of physical batch | Annual obligation in RTFCs (main + dev sub-target), reconciled by 15 Sep of year following |
| Currency of obligation | n/a (declaration scheme) | RTFC, dRTFC, or buy-out cash (£0.50 / £0.80 per missing cert) |

The DFT plant is on the *production* side of this chain. If pyrolysis output is exported to a UK obligated supplier, the RTFC is **awarded to the UK supplier** at point of duty (or alt-assessment point), but the supplier needs the upstream sustainability + GHG evidence that DFT produces.

---

## 2. Likely RTFO classification of Girardot output

Per `docs/rtfo-essential-guide.md` §6:

- **RCF (Recycled Carbon Fuel):** fuel made from a fossil waste that cannot be recycled, reused or prevented, AND designated as relevant feedstock by the LCF Delivery Unit. Uses **Annex D counterfactual GHG methodology**. Awarded **1 dRTFC per litre** equivalent. No double-count.
- **Double-counting waste / residue (general dRTFC):** typically biogenic — used cooking oil, animal fats, agricultural residues. **2× dRTFCs per litre**.

**ELT (end-of-life tyres)** is fossil-origin material (synthetic rubber + carbon black + steel) → **RCF route**, **1 dRTFC/litre**, **Annex D GHG**. No biogenic share expected; C14 analyses on `daily_inputs` confirm fossil dominance. The "biogenic vs fossil split" concept — useful for mixed feedstocks like lignin or biomass-derived rubber — does not apply to the pure-ELT case.

**Implication:** for RTFO the DEV-P100 stream is single-class **RCF**. The original two-stream model (biogenic vs fossil) degenerates: the entire volume sits on the Annex D / 1 dRTFC path. `theor_veg_pct` + `manuf_veg_pct` + `c14_value` remain useful as physical "no biogenic" evidence for ISCC + DfT inspections, not as a product-split driver.

---

## 3. Gap inventory (field-by-field)

### 3.1 Feedstock classification

| What RTFO needs | DFT today | Gap |
|---|---|---|
| Feedstock matches **List of Feedstocks** (pre-approved) or assessment pending | `suppliers` only — no feedstock entity | **MISSING** — no `feedstock` table, no link feedstock→input row |
| Feedstock type: waste / residue / dedicated energy crop / biomass / fossil-waste-RCF | implicit in supplier name | **MISSING** — no enum, no per-row tag |
| Eligibility for double-counting | n/a | **MISSING** |
| RCF designation by LCF Delivery Unit | n/a | **MISSING** |

**Recommendation:** new `feedstocks` table + FK on `daily_inputs.feedstock_id`. Enum column for `rtfo_class` ∈ `{relevant_crop, general_waste, double_counting_waste, rcf, rfnbo, ineligible}`. Seed with the published *List of Feedstocks*.

### 3.2 GHG carbon intensity

| What RTFO needs | DFT today | Gap |
|---|---|---|
| Per-batch CI in gCO₂eq/MJ (or per litre) | not tracked | **MISSING** |
| ≥ 55–65% GHG saving vs fossil counterfactual (94 gCO₂eq/MJ baseline for biofuels) | not enforced | **MISSING** |
| Annex D counterfactual methodology for RCF | not implemented | **MISSING** |
| Integration with DfT Carbon Calculator output | none | **MISSING** |

**Recommendation:**
- New table `ghg_calculations` keyed by `(daily_production_id, methodology_version)` storing input CI per stage (cultivation/collection, processing, transport), final CI, % saving vs counterfactual, and a `methodology` enum ∈ `{red_ii_default, red_ii_actual, annex_d_counterfactual}`.
- A column `daily_production.ghg_calculation_id` (nullable).
- Import-only first iteration: accept CI from spreadsheet → store + validate threshold → block RTFC application if below threshold.

### 3.3 RTFC inventory

| What RTFO needs | DFT today | Gap |
|---|---|---|
| Certificates issued per litre/kg-eq | n/a (ISCC is a declaration scheme, not a tradeable cert per unit) | **MISSING entirely** |
| RTFC class: general / relevant crop / dRTFC | n/a | **MISSING** |
| Award / redeem / sell / buy-out events | n/a | **MISSING** |
| 25% carry-over from prior period, single-year only | n/a | **MISSING** |

**Recommendation:** new module `rtfc_ledger` with tables:
- `rtfc_batch(id, obligation_period_year, class enum, litres_eligible, dRTFC_qty, RTFC_qty, ghg_calculation_id, daily_production_id, status)`
- `rtfc_event(id, batch_id, event_type enum {awarded, redeemed, sold, bought, carried_over, bought_out}, qty, counterparty, price_per_cert, event_date)`
- View `rtfc_balance(obligation_period_year, class)` for live obligation position.

### 3.4 Supplier & verifier registry

| What RTFO needs | DFT today | Gap |
|---|---|---|
| Independent verifier identity per RTFC application | not tracked | **MISSING** |
| Recognised voluntary scheme link (ISCC EU is one route) | `Certificate.scheme` field — already a string | **PARTIAL** — string-typed, no enum, no DfT-recognised-list check |
| Buyer = UK obligated supplier | **Crown Oil UK identified** as sole project off-taker (Europe excluded) — not yet modelled in schema | **MISSING** — no `customer` / `off_taker` entity in schema, but counterparty known |

**Recommendation:**
- New `off_takers` table for downstream UK suppliers receiving the pyrolysis oil.
- New `verifiers` table + `rtfc_batch.verifier_id` FK.
- Migrate `Certificate.scheme` to enum-constrained `{ISCC EU, REDcert, 2BSvs, RSB, KZR INiG, ...}` matching the DfT recognised list.

### 3.5 ROS-shaped reporting export

| What RTFO needs | DFT today | Gap |
|---|---|---|
| Volume submission via **ROS** (RTFO Operating System) validated against HMRC duty data | xlsx import only; no UK transport supply tracking | **MISSING** |
| Per-product volumes in **litres** (ROS unit) | **AVAILABLE**: `mv_mass_balance_monthly.eu_prod_litres` + `plus_prod_litres` via `product_densities` lookup (EU 0.78, PLUS 0.856 kg/L — EAD-confirmed 2026-05-13) — migration 0005 | **UNBLOCKED** |
| Per-batch traceability from feedstock → final UK transport supply | mass-balance ends at plant gate | **MISSING last-mile** — DFT→Crown Oil UK chain still to model |
| Independent verification artefact bundle (PDF + supporting data) | ISCC PDF cert generation planned | **PARTIAL** — adapt the planned PDF generator to also produce an ROS-compatible report |

**Recommendation:**
- Define a `rtfo_export` view producing the data shape ROS expects (per published ROS schema — needs separate fetch).
- Versioned export jobs in audit log; re-run idempotently for restatements.

### 3.6 Sustainability criteria (land / forest / soil carbon)

**Status: N/A confirmed for ELT-only scope.** Feedstock = end-of-life tyres = post-consumer fossil material. RTFO land/forest/soil-carbon criteria apply only to biogenic feedstocks (energy crops, agri residues, forest biomass). For the ELT → RCF stream this section is benign and requires no schema storage.

| What RTFO needs | DFT today | Gap |
|---|---|---|
| Land criteria | not tracked | **N/A** for ELT/RCF |
| Forest criteria | not tracked | **N/A** for ELT/RCF |
| Soil carbon | not tracked | **N/A** for ELT/RCF |

**Recommendation:** keep benign. Only if a biogenic feedstock (lignin, biomass char) ever enters the plant would `feedstock.sustainability_attestation_url` become needed.

### 3.7 Obligation lifecycle & deadlines

| What RTFO needs | DFT today | Gap |
|---|---|---|
| Calendar 1 Jan → 31 Dec obligation period | DFT operates on calendar year via `prod_date` natural year | **PARTIAL** — usable but no explicit `obligation_period` entity |
| 15 September following-year deadline reminders | none | **MISSING** — no reminder/notification subsystem |
| Buy-out option at £0.50 / £0.80 per missing cert | n/a | **MISSING** — finance ledger needed |

---

## 4. What DFT *already* covers usefully

These elements need extension but not redesign:

- **`daily_inputs` + `daily_production` mass-balance** with materialised views — the kg-in / kg-out skeleton for any sustainability scheme.
- **Supplier registry + supplier_certificates many-to-many** — generic enough to host RTFO-recognised voluntary schemes alongside ISCC EU.
- **`audit_log`** — already records who/when/what for daily_entries; extends naturally to RTFC awards/redeems/sells.
- **`source_file` + `source_row` traceability** — every input/production row pointable back to original xlsx; an RTFO verifier inspection would value this.
- **Soft delete (`deleted_at`) discipline** — no destructive history rewrites; required posture for ISCC audits and equally for RTFO verification.
- **C14 analysis fields** (`c14_value`, `c14_analysis`) — direct physical evidence of biogenic share, useful both for ISCC and to prove to DfT that the ELT stream is ~100% fossil (RCF classification precondition).
- **`product_densities` (migration 0005)** + `eu_prod_litres` / `plus_prod_litres` columns in `mv_mass_balance_monthly` — kg→litres conversion ready, ROS-compatible unit.

---

## 5. Recommended implementation phasing

**Phase 1 — Read-only readiness (no UK supply yet, prep only)**
1. New `feedstocks` table + FK from `daily_inputs`. Seed from RTFO List of Feedstocks.
2. Per-batch GHG CI storage (`ghg_calculations`) — manual upload only.
3. Scheme enum on `certificates`.

**Phase 2 — If/when an RTFO-obligated UK off-taker engages**
4. `off_takers` + `verifiers` tables.
5. `rtfc_batch` + `rtfc_event` ledger.
6. Carry-over view (25%, single-year forward).

**Phase 3 — Reporting + automation**
7. ROS export format + scheduler.
8. 15-Sep deadline reminders + buy-out ledger.
9. PDF verifier bundle (extends planned ISCC PDF generator).

**Phase 4 — GHG automation**
10. Implement Annex D counterfactual methodology for the RCF stream in code; integrate with DfT Carbon Calculator (CSV import or API if available).

---

## 6. Non-goals / explicitly out-of-scope

- Implementing RTFO logic *before* a UK obligated off-taker exists. Premature build risks divergence from the eventual ROS schema and Annex D methodology updates.
- Replacing ISCC EU tracking. ISCC EU remains the primary voluntary scheme used; RTFO sits *alongside* it for fuel routed into UK transport.
- Forest / land / soil criteria fields beyond a free-form attestation URL until a biogenic feedstock actually enters the plant.

---

## 7. Open questions for the client

1. ~~Is any current or near-term off-taker a UK obligated supplier?~~ **RESOLVED 2026-05-13:** Crown Oil UK confirmed as sole project buyer, Europe excluded. Actual volume ≥ 450 kL/yr UK to be verified with them.
2. ~~What fraction of output is biogenic vs fossil?~~ **RESOLVED:** ELT feedstock = 100% fossil (synthetic rubber/carbon black/steel). No biogenic split, single RCF stream.
3. **OPEN:** Has ELT (end-of-life tyres) been formally designated by the LCF Delivery Unit as an RCF-eligible feedstock? If not, designation request is the precondition for any RTFC award. (Action plan 2026-05: Track A = retro-eligibility bundle Jan 2025 with designation request.)
4. **OPEN:** Does Crown Oil contract on a *physical* (segregated) or *mass-balance* basis? Clarify pre/post Crown Oil meeting.
5. **OPEN (new):** which RTFO-recognised independent verifier will be appointed for the DEV-P100 bundle? (Saybolt NL handles C14 ISCC but is not a UK RTFO verifier.)

---

## 8. Document maintenance

- Re-read source guide on each yearly obligation-percentage update (next: 2026 values, published ahead of obligation period 2026).
- Cross-check against `docs/rtfo-essential-guide.md` after any DfT essential-guide revision.
- Keep this gap doc in sync with schema migrations: each new RTFO-supporting migration should reference the gap section it closes.

---

## 9. Changelog

**v2 — 2026-05-15**
- Header: feedstock corrected from "plastic/tyre/rubber" to **ELT (end-of-life tyres) only**; migration count 3→5; added Crown Oil UK as confirmed off-taker.
- §0: realigned to ELT-only scope and known buyer.
- §2: removed two-stream model (biogenic/fossil); simplified to single-class RCF.
- §3.4: Crown Oil UK identified (schema entity still missing).
- §3.5: added "volumes in litres AVAILABLE" row via `product_densities` + `mv_mass_balance_monthly` (migration 0005).
- §3.6: N/A status confirmed for ELT-only scope.
- §4: added `product_densities` + litres in materialised views as ready asset.
- §7: Q1 and Q2 resolved; Q3/Q4 open; Q5 new (RTFO verifier).
- Cross-refs added to `dft-action-plan-2026-05.md` and `dft-5wd-activity-plan.md`.

**v1 — 2026-05-12**
- Initial version, ISCC EU baseline + 6 gap areas.
