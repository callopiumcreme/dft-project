# Mass-Balance Allocation Policy — OisteBio Girardot (CO)

**Version**: 1.0
**Effective from**: 2026-05-24
**Owner**: OisteBio GmbH (Baar, CH)
**Scope**: ELT-derived pyrolysis oil (DEV-P100), Girardot plant (CO) → Crown Oil Ltd (UK) via Cartagena Contecar (CO) → UTB Rotterdam (NL).
**Regulatory references**: ISCC-EU §5 (Mass Balance), UK RTFO Guidance (Renewable Transport Fuel Obligation), DfT Carbon Reporting.

---

## 1. Purpose

This document defines, in audit-defensible terms, how OisteBio attributes
production output (kg of DEV-P100) and feedstock input (kg of ELT) to
individual downstream consignments. It is the **single allocation rule** used
by the chain-of-custody ledger (`mass_balance_ledger`) and by every
derived view, widget, and export (audit pack, eRSV documents, RTFO bundle).

This policy is required because OisteBio operates under a **mass-balance
chain of custody** model (ISCC-EU §5), in which physical 1:1 traceability
from feedstock lot to product container is not required and is not claimed.
What is required, and what this policy implements, is a deterministic,
documented, replicable allocation rule applied uniformly across all
consignments in a given mass-balance period.

## 2. Definitions

| Term | Meaning |
|------|---------|
| **Plant** | OisteBio pyrolysis facility, Girardot (CO). |
| **Feedstock** | End-of-life tyres (ELT) entering the plant. Tracked by `daily_inputs.total_input_kg`, one row per supplier per day. Each row carries an inbound eRSV document number. |
| **Production day** | One row in `daily_production`. `output_eu_kg` = kg of EU-certified DEV-P100 produced that day from the running mass balance. |
| **Consignment** | A logical delivery commitment from OisteBio to one off-taker, covering a contiguous production window. Identified by `consignment.code` (e.g. `DEL-CRW-2025-2`). |
| **Allocation** | The act of attributing kg of plant production to a consignment. Recorded as one row per `(consignment_id, prod_date)` pair in `consignment_production_link`. |
| **MB period** | The plant's mass-balance accounting period (calendar quarter). Consignments are bounded by `prod_date_from..prod_date_to` and must fall within a single MB period. |

## 3. Allocation rule

### 3.1 Single rule

For every consignment `C` with `prod_date_from = F` and `prod_date_to = T`:

```
For each prod_date D in [F, T]:
    let plant_kg(D)  = SUM(daily_production.output_eu_kg) WHERE prod_date = D
    let total_window = SUM(plant_kg(D)) for D in [F, T]
    let C_demand     = C.total_kg

    kg_allocated(C, D) = plant_kg(D) * (C_demand / total_window)
```

In words: **each production day in the consignment's window contributes to
the consignment proportionally to the kg produced that day, scaled so the
sum over the window equals the consignment's declared total.**

This is the **kg-proportional weighted-by-daily-production** rule.

### 3.2 Numeric example (Q3-2025)

| Input | Value |
|-------|-------|
| Consignment | `DEL-CRW-2025-2` |
| Window | 2025-06-01 … 2025-08-31 |
| Production days in window | 74 |
| Plant Q3 total output (EU) | 3 014 511,546 kg |
| Consignment demand | 576 270,000 kg |
| Scale factor | 576 270 / 3 014 511,546 ≈ **0,19116** |

For an example production day with `output_eu_kg = 42 100,000`:
```
kg_allocated = 42 100 × 0,19116 = 8 047,84 kg → recorded for that prod_date
```

Sum over 74 days = 576 270,000 kg (= `consignment.total_kg`) by construction.

### 3.3 Multi-consignment overlap

If two or more consignments overlap on a single production day, allocation
is performed **simultaneously and proportionally to the unsatisfied demand**:

```
For each prod_date D:
    let plant_kg(D) = SUM(daily_production.output_eu_kg) WHERE prod_date = D
    let active_C    = { C : F_C ≤ D ≤ T_C, C not yet fully satisfied }
    let total_demand_D = SUM(C.remaining_demand for C in active_C)

    For each C in active_C:
        kg_alloc(C, D) = plant_kg(D) * (C.remaining_demand / total_demand_D)
        C.remaining_demand -= kg_alloc(C, D)
```

This guarantees no double-counting and that the total plant output is
always conserved (each kg goes to exactly one consignment or remains in
plant stock).

### 3.4 Plant stock residual

```
plant_stock(D) = SUM(plant_kg(d) for d ≤ D)
              - SUM(kg_alloc(any C, d) for d ≤ D)
```

Positive residual = uncommitted product available for future consignments.
Recorded daily by the ledger as `event_type='production'` rows with
`kg_in = output_eu_kg`, `kg_out = 0`, balanced subsequently by
`event_type='consign_assign'` rows.

## 4. Feedstock-side accounting

Feedstock-to-product traceability **does not require 1:1 lot mapping**
under ISCC-EU mass-balance rules. The plant ledger documents:

1. **Inbound credits**: each `daily_inputs` row creates one
   `event_type='inbound'` ledger entry with `kg_in = total_input_kg` and
   `ref_doc_no = ersv_number`. This represents kg of ELT credited to the
   plant mass-balance account.
2. **Production debits**: each `daily_production` row creates one
   `event_type='production'` ledger entry. `kg_in` records the EU-certified
   output kg. The corresponding feedstock debit is **not** allocated to
   specific inbound rows; instead the running plant feedstock balance is
   debited proportionally to ELT-out (= `kg_to_production`).

This means a consignment's upstream traceability is expressed as:
> "Material in this consignment was produced at Girardot during
> `[F, T]`, drawing from the plant ELT mass-balance account which received
> N inbound consignments documented by inbound eRSV in the same MB
> period, totalling M kg ELT certified ISCC-EU."

NOT as:
> ~~"Container PCVU3502178 is derived from tyres delivered under inbound
> eRSV 23/2025-06-12/05."~~ (would be physical-traceability claim, not
> supportable, not required.)

## 5. What goes in signed PDFs vs the ledger

| Artefact | Contents |
|----------|----------|
| **Inbound eRSV** (existing) | Supplier, kg ELT, supplier certificate ISCC, date. No downstream references (information not available at issue time). |
| **Inland eRSV** (Girardot→Cartagena, per container) | Consignment code, prod window `F..T`, total feedstock kg in window, count of inbound eRSV in window. No explicit eRSV number list. |
| **Outbound eRSV** (Cartagena→UK, per PoS) | Consignment code, prod window, total feedstock kg, count of inbound eRSV, count of inland eRSV. No explicit eRSV number list. |
| **Ocean BL notes** | Consignment code, container count, inland eRSV seq range. No 15-line container list. |
| **Audit Pack PDF** (on demand, derived from ledger) | Full ledger extract for consignment: every event, every kg, every doc reference, running balance, signed by CEO with timestamp + hash. Given to Crown Oil / DfT on request. |
| **Dashboard widget** (`/app/logistics/{id}`) | Live read of `v_chain_summary`. Same data as audit pack, browsable. |

**Rule**: the signed PDF never contains a list of upstream document numbers
that could be invalidated by a single typo. It references the consignment
and the rule; the ledger provides the detail.

## 6. Corrections and append-only invariant

The `mass_balance_ledger` table is **append-only with soft-delete**:

- Errors are corrected by:
  1. `UPDATE mass_balance_ledger SET deleted_at = NOW() WHERE id = X` (mark wrong row)
  2. `INSERT INTO mass_balance_ledger (...) VALUES (..., notes='corrects #X')` (issue correction)
- Hard `DELETE` is **forbidden** by application policy.
- Audit trail = the chronological history of all rows including superseded
  ones.

## 7. Governance

- This document is the **policy of record**. Any deviation (e.g. switching
  to FIFO allocation, or weighted-by-feedstock-mix) requires a versioned
  amendment signed by the CEO of OisteBio GmbH and notified to Crown Oil
  Ltd before the next mass-balance period closes.
- Application code that performs allocation **must** reference this
  document by version in its docstring / commit message.
- Sign-off:

```
OisteBio GmbH
Paolo Ughetti, Geschäftsführer
Date: ____________________
Signature: ____________________
```

---

*End of policy v1.0*
