# DFT-C1 — Internal Audit Recheck

**Date:** 2026-06-01
**Author:** Internal (FMS / data-system side)
**Scope:** Re-evaluation of the DfT C1 audit posture as of today, reconciling the
internal auto-audit (16 criteria, last closed Round-5 / 2026-05-27) against the
**external DfT formal rejection letter of 9-Mar-2026** and Deeba Rehman's 5
follow-up questions. Consignment in scope: **DEL-CRW-2025-2**. Window:
**Jan–Aug 2025**. Single buyer: Crown Oil UK (Europe excluded). Byproduct buyer:
Conquer Trade (DEV-P200).

> **Method discipline.** Every quantitative claim below was verified directly
> against the **production** DB and repo on 2026-06-01 before being written
> (`feedback_verify_before_report`). Where a fact is upstream / supply-chain and
> cannot be settled from our system, it is flagged explicitly as **out-of-system**
> — not asserted as resolved.

---

## 0. Executive verdict

**Two-track reality. They disagree, and the disagreement is the headline.**

- **Internal track (our data system):** **strong and improving.** Auto-audit was
  PASS at Round-5 (15/16, 1 deferred) on alembic `0041`. Prod is now at `0047` —
  six migrations of additional cleanup/schema beyond the last verdict, plus two
  shipped UI features (supply-data-sheet PDF, Doc ID column) that improve evidence
  traceability. Mass balance closes (Mar–Aug = 0.0000%, Jan/Feb = documented
  symmetric carry-over). kg→litres production logs **exist and are fully
  populated** (194/194 rows).

- **External track (DfT regulator):** **NOT passed.** The 9-Mar-2026 letter
  **rejected** the submission and DfT **deleted 5 RTFO bundles** on 13-Mar-2026.
  ROS resubmission deadline (14-May-2026) **PASSED**. The four DfT findings are
  mostly **upstream supply-chain certification facts** (ISCC certification of EoL
  tyre collection points; tyre-handling registration of feedstock providers) that
  a clean internal data system **cannot fix by itself**.

**Bottom line:** internal "PASS" is **necessary but not sufficient**. A green
auto-audit means our ledger is coherent and defensible; it does **not** mean DfT
will accept the chain. The remaining blockers are predominantly **out-of-system**
and require Crown Oil + supplier action, not more migrations.

---

## 1. State delta since Round-5 (2026-05-27 → 2026-06-01)

| Axis | Round-5 | Now (2026-06-01) | Verified |
|------|---------|------------------|----------|
| Alembic head (prod) | `0041` | **`0047_c14_certificate_schema`** | `alembic_version` on prod |
| Active certificates | — | **15** (6 with PDF, 6 in-window without, 3 placeholders) | `certificates WHERE deleted_at IS NULL` |
| Active suppliers | — | **8** | `suppliers WHERE deleted_at IS NULL` |
| Daily inputs | — | **2047** rows, 2025-01-02 → 2025-08-30 | `daily_inputs` |
| Daily production | 194 days | **194** rows, all with litres | `daily_production` |
| Product purchases | — | **51** | `product_purchases` |
| Byproduct sales | — | **8** | `byproduct_sale` |
| AUDIT-MISMATCH cert notes | — | **2** | `certificates.notes LIKE '%AUDIT-MISMATCH%'` |

**Migrations added since last verdict:**

- `0042_d17_cosmetic_fixture_cleanup` — cosmetic / fixture hygiene.
- `0043_byproduct_sale_pdf_ref` — byproduct sale → PDF reference link.
- `0044_retire_ecogras_2025_cert` — soft-deprecate ECOGRAS 2025 cert (ES216-20254036).
- `0045_le5ton_cert_drift_cleanup` — LE5TON self-decl bucket drift cleanup
  (canonical NULL pattern, `project_le5ton_no_pos`).
- `0046_product_purchases_schema` — product-purchases model (powers supply-data-sheet).
- `0047_c14_certificate_schema` — C14 certificate schema (current head).

**Features shipped to prod since last verdict:**

- **Supply Data Sheet** (proforma PDF) — `templates/reports/proforma_invoice.html`,
  renders per `product_purchase`, explicitly **"not a fiscal invoice"** (data-
  presentation sheet honoured by supplier's own commercial invoice). Render
  verified `200 application/pdf %PDF`.
- **Doc ID column** in `/app/inputs` — sha256(16-hex) of the canonical eRSV row,
  1:1 with the printed eRSV PDF header; opens the same eRSV modal as mass-balance.
  Replaces the raw eRSV column. Verified via Playwright on prod.

---

## 2. Internal 16-criteria recheck (carry-forward from Round-5)

Round-5 was **15 PASS / 0 FAIL / 1 DEFERRED**. Recheck today: all 15 PASS criteria
remain structurally satisfied at `0047` (no regressions found; mass balance still
closes, no orphan inputs, legacy suppliers/certs still retired). **C16 (driver /
cedula / plate schema) remains DEFERRED** — columns still absent, still awaiting
client DRIVERS input (B1–B4). This is unchanged and remains **not an audit blocker
for the Crown Oil bundle** by the Round-5 definition.

**Net:** internal matrix holds. No new internal FAIL introduced by `0042–0047`.

---

## 3. DfT 9-Mar-2026 rejection letter — finding-by-finding reconciliation

Verbatim findings (source: `docs/audit-dft-c1-deeba-realign/2026-05-29-morning-pending-notes.md`).

### F1 — ISCC certification of the tyre collection points
> "the submitted evidence did not sufficiently demonstrate that the EoL tyres were
> supplied by ISCC certified collection points … DfT do not therefore consider any
> of the supply chain to be ISCC certified"

- **Severity:** 🔴 highest. This invalidates the chain at the root.
- **In-system status:** we hold supplier certificates (15 active; **6 in-window
  certs without a PDF on file**, plus 3 by-design placeholders — see weakness W1)
  and chain-of-custody narrative post-0044/0045.
- **Out-of-system gap:** whether the **collection points** that feed the tyre
  suppliers are themselves ISCC certified is **not a fact our DB can manufacture**.
  It requires the supplier's upstream ISCC scope certificate naming the collection
  points, or DfT-acceptable equivalent. **Crown Oil + suppliers must supply this.**
- **Action:** obtain ISCC PoS / scope certs that explicitly cover the EoL-tyre
  collection points for the tyre-side suppliers (KAL TIRE / BOLDER / EFFICIEN /
  PYRCOM), attach PDFs, bind to `certificates` rows.

### F2 — Incomplete feedstock records + "production logs to litres not provided"
> "Records of feedstock material received were incomplete or inconsistent;
> production logs detailing conversion to litres were not provided despite being
> requested"

- **Severity:** 🟠 → **largely RESOLVED in-system.**
- **litres part:** **RESOLVED.** `daily_production` has `litres_eu` + `litres_plus`
  populated on **194/194** rows (Σ EU = 9,502,019 L, Σ PLUS = 11,815,843 L,
  verified today). The MV `mv_mass_balance_monthly` exposes `eu_prod_litres /
  plus_prod_litres / total_prod_litres` per month. The letter photographed a
  **pre-Sprint-2** state; the conversion logs now exist and are queryable.
- **feedstock-records part:** **partially open.** Daily inputs are complete and
  orphan-free (2047 rows, Jan2–Aug30, supplier+cert FK clean). But the **feedstock
  type/material is not modelled as a structured column** — `suppliers` has no
  `feedstock_type`, and there is no per-row material classification (Sprint α
  "feedstocks model" is DEFERRED post-audit). DfT's "inconsistent" likely refers to
  the **Jan plastics/organics → Feb ELT pivot** (`project_feedstock_elt`), which is
  a real historical mix, not a data defect — but it needs a **clear narrative**, not
  a schema change.
- **Action:** (a) re-state the litres logs are now provided (regenerate the export);
  (b) write the feedstock-mix narrative for Jan vs Feb–Aug explicitly.

### F3 — Feedstock providers not registered to handle tyres
> "no evidence that most feedstock providers associated with the fuel were
> registered to handle tyres"

- **Severity:** 🔴 high, **out-of-system.**
- **In-system status:** 8 active suppliers — tyre-side = **KAL TIRE (CL), BOLDER
  (US), EFFICIEN (US), PYRCOM (CO)**; plastics/organics-side = **LITOPLAS,
  BIOWASTE, ESENTTIA (all CO)** + **LE5TON** (≤5 TON aggregate self-decl, CO).
- **Mismatch risk (open):** the DFTEN-108 ANLA folder skeleton
  (`04_feedstock_provider_authorisations/`) currently covers the **plastics/organics**
  trio (Litoplas/Biowaste/Esenttia). DfT asks for **tyre-handling** registration.
  **The folder scope and the ask may not line up** — this is the unresolved
  hypothesis from 2026-05-29 (item A) and is **still not closed**.
- **Action:** confirm with Crown Oil/Paolo **which suppliers are the actual EoL-tyre
  providers in scope for DEL-CRW-2025-2**, then collect each one's tyre-handling
  authorisation (e.g. ANLA / environmental permit naming tyres). This is a
  document-collection task, not a code task.

### F4 — Production-site inconsistencies (images / capacity / start dates)
> "production site images, capacity of the production facility and production start
> dates" [inconsistent]

- **Severity:** 🟡 medium, **out-of-system / documentary.**
- **In-system status:** nothing in the DB speaks to plant photos / nameplate
  capacity / commissioning dates. These live in the narrative bundle.
- **Action:** assemble a single coherent production-site fact sheet (photos +
  capacity + start date) and make sure every bundle document quotes the **same**
  numbers. Pure documentary consistency.

---

## 4. Deeba's 5 follow-up questions — status

| # | Question | Status | Owner |
|---|----------|--------|-------|
| 1 | End-to-end cycle feedstock → fuel (origin/collecting point → received → conversion) | 🟡 partial — internal ledger (inputs→production→litres→consignment) exists; **collecting-point origin** is the gap | FMS + supplier docs |
| 2 | Review 3-supply-chain diagram (attached) | ⏳ pending client artefact | Crown Oil / Paolo |
| 3 | Are Litoplas/Biowaste/Esenttia collecting points? If not, give actual ones | 🔴 open — these are plastics/organics suppliers, **not tyre collection points**; actual tyre collection points must be named | supplier docs |
| 4 | Are Litoplas/Biowaste/Esenttia ALL 2025 feedstock providers? | 🔴 needs honest answer — **no.** Tyre-side (KAL TIRE/BOLDER/EFFICIEN/PYRCOM) also in 2025; Jan was plastics/organics, Feb+ ELT | client confirm |
| 5 | 2024 records — include collecting point/origin if missing | ⚪ out of audit window (Jan–Aug 2025) — clarify whether 2024 is even in scope | Crown Oil |

**Q3 + Q4 are the crux.** Answering them truthfully exposes the Jan-plastics →
Feb-tyres pivot and forces naming the real EoL-tyre collection points. That is the
same root as F1/F3.

---

## 5. Strengths (punti forti)

- **S1 — Mass balance is auditable and it closes.** Mar–Aug closure = **0.0000%**;
  Jan/Feb deviation is a **documented symmetric ±339,865 kg carry-over** (Jan
  −10.05%, Feb +12.83% — same kg, different denominators), not a defect
  (`project_jan_feb_stock_carryover`). 8 months, 194 production days, no duplicate
  `prod_date`, no orphan inputs.
- **S2 — kg→litres conversion logs now exist (the F2 litres ask is answerable).**
  194/194 production rows carry litres; MV exposes monthly litres. Directly rebuts
  the "not provided" finding for current state.
- **S3 — Clean, monotonic data hygiene.** Six additive migrations (0042–0047)
  since the last verdict, each with audit-log provenance; legacy suppliers/certs
  soft-deprecated (never hard-deleted); LE5TON canonical NULL pattern enforced.
- **S4 — Evidence traceability improved at the UI.** Doc ID column makes every eRSV
  row click-through to its signed PDF (hash 1:1 with the printed header); supply-
  data-sheet gives a clean, **non-fiscal** per-purchase quantity artefact that
  doesn't masquerade as an invoice (important for audit honesty).
- **S5 — Soft-delete + audit-log discipline holds.** `audit_log.action` CHECK
  respected throughout (schema extends tagged as `action='update'` +
  `new_values.kind`); no historical compliance data silently rewritten
  (`project_iscc_audit_safety`).
- **S6 — Single, clean buyer topology.** Crown Oil = sole DEV-P100 buyer (Europe
  excluded); Conquer = sole DEV-P200 byproduct buyer. No ambiguous multi-buyer
  attribution to defend.

## 6. Weaknesses (punti deboli)

- **W1 — 6 in-window ISCC certificates have no PDF on file** (refined 2026-06-01).
  Of the 9 active certs without a PDF, **3 are placeholders** (`PLACEHOLDER`, `SD`,
  `SELF DECL. ISCC`) — empty **by design** (LE5TON ≤5 TON self-declaration,
  `project_le5ton_no_pos`), **not** gaps. The remaining **6 are real certs that
  cover the Jan–Aug 2025 window but carry no PDF** — the single most exploitable
  internal gap, since a cert row without an attached document is **not** audit
  evidence. **Direct hit on F1.**

  | cert | scheme | exp | covers window | PDF |
  |------|--------|-----|---------------|-----|
  | CO222-00000026 | ISCC EU | 2025-10 | ✓ | — |
  | CO222-00000027 | ISCC EU | 2025-10 | ✓ | — |
  | ES216-20249051 | ISCC PLUS | 2025-10 | ✓ | — |
  | US201-120372025 | ISCC EU | 2026-04 | ✓ | — |
  | US201-138762025 | ISCC EU | 2026-05 | ✓ | — |
  | US201-158772025 | ISCC EU | 2026-01 | ✓ | — |

  **Audit window = Jan–Aug 2025; expiry dates beyond Aug 2025 are NOT a concern**
  (the cert is valid for the whole window) — only the missing PDF is. The three
  **US201-2025** renewals are **not** cosmetic: their 2024 PDF siblings expire
  **inside** the window (US201-158772024 exp 2025-01-25, US201-120372024 exp
  2025-04-03, US201-138762024 exp 2025-05-17), so the 2025 versions are what cover
  **May–Aug 2025** — and those lack PDFs. **Action: attach the 6 PDFs (priority:
  the 3 CO222/ES216 + the 3 US201-2025 renewals); the 3 placeholders stay empty.**
- **W2 — Feedstock material is not modelled.** No `feedstock_type` on `suppliers`,
  no per-input material class. The Jan-plastics/Feb-tyres reality lives only in
  prose. DfT reads that as "inconsistent" (F2). Sprint α would fix this but is
  DEFERRED — so for **this** submission it must be covered by narrative.
- **W3 — ANLA folder scope vs DfT ask may be misaligned.** Folder covers
  plastics/organics trio; DfT wants **tyre**-handling registration (F3). Unresolved
  since 2026-05-29. Risk: we deliver authorisations for the wrong suppliers.
- **W4 — The hardest findings are out-of-system and depend on third parties.**
  F1 (collection-point ISCC) and F3 (tyre-handling registration) **cannot** be
  closed by us. They depend on Crown Oil + suppliers producing real upstream
  documents. Internal readiness ≠ submission readiness.
- **W5 — Deadlines already passed.** ROS resubmission deadline **14-May-2026
  PASSED**; 5 bundles **deleted 13-Mar-2026**. Resubmission path/relationship needs
  Crown Oil to re-open with DfT — we don't control that timeline.
- **W6 — Internal "PASS" risks false confidence.** The auto-audit green can be
  misread as "audit won." It only certifies ledger coherence. **This is the failure
  mode of 2026-05-29** (claiming closure without verifying scope). Keep the two
  tracks explicitly separate in all client comms.
- **W7 — Mass-balance closure is model-derived, not independently measured.**
  Mar–Aug = exactly 0.0000% because output is derived from input by the model. Not
  an error for current audit, but it is **not an independent reconciliation** — if
  DfT asks for independently-metered output, we have a story gap.
- **W8 — DEL-CRW-2025-1 has no reconstructable upstream chain** (pre-FMS v1.0,
  `project_del_crw_2025_1_out_of_scope`). Fine **as long as DfT agrees scope = only
  DEL-CRW-2025-2.** If scope creeps, this becomes a hole.

---

## 7. Risk register (open items, prioritised)

| Pri | Item | Track | Blocker for resubmission? |
|-----|------|-------|---------------------------|
| P0 | F1 — ISCC certification of tyre collection points | out-of-system | **YES** |
| P0 | F3 — tyre-handling registration of real tyre suppliers | out-of-system | **YES** |
| P0 | W5 — ROS deadline passed; Crown Oil must re-open with DfT | out-of-system | **YES (process)** |
| P1 | W1 — 6 in-window certs missing PDFs (3 placeholders excluded) | in-system | strong contributor to F1 |
| P1 | W3 — ANLA folder scope alignment (Q3/Q4) | mixed | YES if wrong suppliers |
| P2 | F2 feedstock narrative (Jan plastics → Feb tyres) | in-system (prose) | partial |
| P2 | F4 — production-site fact sheet consistency | documentary | medium |
| P3 | C16 driver/cedula schema | in-system | no (deferred, Conquer side-track) |

---

## 8. Recommended actions before any resubmission

**In-system (we can do, LOCAL first, deploy only on explicit word):**

1. **Close W1** — attach the **6 in-window** certificate PDFs (3 CO222/ES216 + 3
   US201-2025 renewals). The 3 placeholders stay empty by design. A cert without a
   PDF is not evidence.
2. **Regenerate the litres export** for DEL-CRW-2025-2 and label it clearly as the
   "production conversion log (kg→litres)" DfT said was missing (F2).
3. **Write the feedstock-mix narrative** (Jan plastics/organics → Feb–Aug ELT),
   citing daily-input dates — turns DfT's "inconsistent" into "intentional pivot,
   here are the dates."
4. **Resolve the 2 AUDIT-MISMATCH cert notes** or document why they stand
   (`project_iscc_audit_safety` — never silently rewrite).

**Out-of-system (Crown Oil + suppliers — we can only assemble, not author):**

5. **F1/F3 evidence pack:** for the actual EoL-tyre suppliers, obtain (a) ISCC
   scope/PoS naming the **collection points**, (b) tyre-handling authorisations.
   This is the make-or-break.
6. **Answer Deeba Q3/Q4 truthfully** — name the real tyre collection points; confirm
   the full 2025 provider list (tyre + plastics), not just the plastics trio.
7. **Confirm scope = DEL-CRW-2025-2 only** with DfT (protects W8).
8. **Crown Oil re-engages DfT** on the resubmission window (W5).

---

## 9. One-line conclusion

Our **data system is audit-ready and improving** (PASS internally, `0047`, litres
done, mass balance closes). The **DfT audit is not won** because the binding gaps —
ISCC certification of tyre collection points and tyre-handling registration of the
real suppliers — are **upstream documents we do not hold and cannot generate**.
Internal green ≠ regulator green. Next move is **document collection via Crown Oil**,
not more code.

---

_Verified against prod DB + repo 2026-06-01. No claim in this document is
unverified-in-system; all out-of-system items are flagged as such._
