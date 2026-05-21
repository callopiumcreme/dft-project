# DFT — Sprint Plan v1 (post-blueprint)

**Date:** 2026-05-15
**Source:** `docs/blueprint-activities.md` (architect output 2026-05-15)
**Total stories:** 68 (epics E1-E6)
**Sprint cadence:** mixed — Sprint 3 is 1-week emergency window (5wd regulatory deadline), Sprints 4-7 are standard 2-3 week iterations gated by client decisions.

---

## Sprint map

| Sprint | Window | Theme | Stories | Status |
|--------|--------|-------|---------|--------|
| Sprint 3 | 2026-05-15 → 2026-05-22 (7d) | 5wd Track A submission RTFO-310125 + Sprint 3 frontend completion | E1 (18) + E2 (11) = 29 | In flight — regulatory deadline Day 7 |
| Sprint 4 | 2026-05-23 → 2026-06-12 (3w) | RTFO Phase 1 prep (read-only feedstock + GHG + scheme enum) | E3 (9) | Planned — minimal client dependency |
| Sprint 5 | 2026-06-13 → 2026-07-10 (4w) | RTFO Phase 2 RTFC ledger | E4 (13) | Blocked by D4 + D5 + D6 |
| Sprint 6 | 2026-07-11 → 2026-08-07 (4w) | RTFO Phase 3 reporting + ROS export + reminders + verifier bundle | E5 (9) | Blocked by D7 + D8 (and E4 completion) |
| Sprint 7 | 2026-08-08 → 2026-09-04 (4w) | RTFO Phase 4 Annex D + Carbon Calculator | E6 (8) | Blocked by D9 + D10 (and E5 completion) |

Total stories: 29 + 9 + 13 + 9 + 8 = **68**.

---

## Per-sprint detail

### Sprint 3 — 5wd Track A submission + frontend completion (2026-05-15 → 2026-05-22)

**Goal:** Submit single coherent RTFO-310125 (January 2025) bundle on ROS by Thu 2026-05-21 23:59 UK time AND close the 10 outstanding Sprint 3 frontend stories (DFTEN-72..81 equivalent) with deploy verification on `oistebio.usenexos.com`.

**Critical path (E1 — 5wd, ordered by Day):**

- Day 1 (2026-05-15 today): **S1.1** decision litres persistence → **S1.2** WeasyPrint setup → **S1.3** pdf_renderer service → **S1.4** endpoint PDF mass-balance → **S1.5** Annex A v1 Jan 2025
- Day 2 (2026-05-16): **S1.6** template hardening + Annex A v2 → **S1.7** migration 0006 supplier rectification → **S1.8** Annex D stock 339.865 kg PDF
- Day 3 (2026-05-17): **S1.9** CSV audit-log export → **S1.10** production conversion log PDF → **S1.11** supply chain diagram → **S1.14** feedstock authorisations folder
- Day 4 (2026-05-18): **S1.12** cover letter v1 draft → **S1.13** ISCC PoS status PDF → **S1.15** internal pre-audit
- Day 5 (2026-05-19): **S1.16** DB snapshot preliminary
- Day 6 (2026-05-20): **S1.17** internal audit + Annex A FINAL → **S1.12** cover letter FINAL → **S1.16** DB snapshot FINAL
- Day 7 (2026-05-21): **S1.18** ROS upload + DfT notification

**Parallelizable work (E2 — frontend, runs alongside E1):**

E2 stories are verification/closure tasks — the codebase is already in flight under `landing/src/app/app/`. Run E2 in parallel with E1 because they touch different files and roles (E1 = backend + bundle, E2 = frontend dev). Sequence within E2 is flexible; recommend:

- Early: S2.1 (shadcn primitives audit) → S2.2 (api client verification) → S2.3 (auth flow) → S2.4 (middleware)
- Mid: S2.5 (layout) → S2.6 (KPI cards) → S2.7-S2.9 (reports)
- Late: S2.10 (anagrafiche) → **S2.11 DoD verification + deploy smoke test** (Day 6-7 gate)

**Blockers / decisions needed:**

- **D1** — DfT extension confirmation (Day 1 EOD blocker for E1 baseline assumption)
- **D2** — `litres` persistence physical vs MV-only (blocks S1.1 / conditional migration 0007)
- **D3** — supplier mapping for migration 0006 (blocks S1.7 Day 2)

**Exit criteria:**

- Bundle `RTFO-310125/` (10 files per §8 of `dft-action-plan-2026-05.md`) uploaded to ROS by Day 7 EOD
- DfT contact emailed with hash manifest
- All 11 Sprint 3 frontend stories closed in Plane, DoD §5 verified
- Deploy smoke test passes on `oistebio.usenexos.com`

---

### Sprint 4 — RTFO Phase 1 prep (2026-05-23 → 2026-06-12)

**Goal:** Build the read-only RTFO data foundation — feedstock taxonomy, GHG calculation storage, certificate scheme enum — without yet implementing the RTFC ledger. System remains usable for ISCC EU; new tables manually populated as RTFO designation work proceeds.

**Critical path (ordered stories):**

1. **S3.1** Fetch RTFO List of Feedstocks (S, doc-only)
2. **S3.2** Migration 0008 feedstocks (M, blocks S3.3 + S3.4 + S3.8)
3. **S3.3** Back-populate `daily_inputs.feedstock_id = ELT` (S, after 0008)
4. **S3.4** Router `/feedstocks` CRUD (M, after 0008)
5. **S3.5** Migration 0009 ghg_calculations (M, parallel after 0008)
6. **S3.6** Router `/ghg-calculations` upload (M, after 0009)
7. **S3.7** Migration 0010 certificate scheme enum (M, can run independently — risk-medium because data-preserving on populated table)
8. **S3.8** Frontend `/app/feedstocks` (M, after S3.4)
9. **S3.9** Frontend `/app/ghg` (L, after S3.6)

**Parallelizable work:** S3.7 (scheme enum) is independent of the feedstock/GHG chain — assign to second dev. S3.8 + S3.9 frontend tracks can start as soon as the corresponding routers are live.

**Blockers / decisions needed:**

- **D5** (ELT designation as RCF by LCF Delivery Unit) — does NOT block E3 itself (we can seed `lcf_designation_status=pending`), but blocks downstream E4 batch creation.

**Exit criteria:**

- 3 migrations applied (0008/0009/0010); all green on staging
- `feedstocks` populated with RTFO list; ELT row with `lcf_designation_status=pending`
- All existing `daily_inputs` back-populated with `feedstock_id` (ELT) and audit logged
- `Certificate.scheme` enum-typed, no data loss
- Manual GHG upload roundtrip verified
- Frontend `/app/feedstocks` + `/app/ghg` deployed
- `docs/rtfo-feedstock-list.md` committed
- `docs/rtfo-gap-analysis.it.md` updated to v3 (§3.1–3.2 closed)

---

### Sprint 5 — RTFO Phase 2 RTFC ledger (2026-06-13 → 2026-07-10)

**Goal:** Implement negotiable ledger of RTFC + dRTFC with state machine, carry-over (max 25%, annual single year forward only), and link batch ↔ ghg_calculation ↔ daily_production ↔ off-taker ↔ verifier.

**Critical path:**

1. **S4.1** Migration 0011 off_takers + Crown Oil seed (M, blocked by D4 — contract_basis decision)
2. **S4.2** Migration 0012 verifiers (M, blocked by D6 — verifier identification)
3. **S4.3** Migration 0013 obligation_periods + 2025/2026 seed (S)
4. **S4.4** Migration 0014 rtfc_batches (L, after 0011/0012/0013)
5. **S4.5** Migration 0015 rtfc_events (M, after 0014)
6. **S4.6** Router `/off-takers` CRUD (M, after 0011)
7. **S4.7** Router `/verifiers` CRUD (M, after 0012)
8. **S4.8** Router `/rtfc-batches` with state machine (L, after 0014 + 0015)
9. **S4.9** Router `/rtfc-events` append-only (M, after 0015)
10. **S4.10** View `rtfc_balance` (M, after 0014/0015)
11. **S4.11** Carry-over 25% endpoint (M, after 0014/0015/0010)
12. **S4.12** Frontend `/app/rtfo/*` shell (L, parallel to backend)
13. **S4.13** Frontend batch detail + transitions (L, after S4.8 + S4.12)

**Parallelizable work:** Migrations 0011-0013 can run in parallel as they have no inter-FK. Frontend S4.12 shell can start the moment routers S4.6/S4.7 are stubbed.

**Blockers / decisions needed:**

- **D4** — Crown Oil contract basis (physical segregated vs mass balance) — blocks S4.1 seed
- **D5** — ELT designated RCF-eligible (blocks meaningful RTFC creation post-deploy, NOT the schema itself)
- **D6** — verifier identified (blocks S4.2 seed + meaningful batch verification)

**Exit criteria:**

- 5 migrations applied (0011–0015)
- Crown Oil + verifier seeded
- State machine `draft → verified → awarded → (redeemed|sold|cancelled)` enforced with 409 on invalid transitions
- Carry-over endpoint enforces `qty ≤ 0.25 × available_balance` and rejects double carry-over
- Frontend RTFO ledger UI deployed; admin can navigate batches/events/balance

---

### Sprint 6 — RTFO Phase 3 reporting + automation (2026-07-11 → 2026-08-07)

**Goal:** Automate the regulatory submission lifecycle — ROS export (idempotent + versioned), reminder scheduler (15-Sep deadline), buyout cash ledger, verifier bundle PDF.

**Critical path:**

1. **S5.1** Fetch ROS schema (M, blocked by D7) — must precede S5.2
2. **S5.2** View + endpoint `/ros-export` (L, after S5.1)
3. **S5.3** Migrations 0016 + 0017 + 0018 (M, parallel to S5.1/S5.2)
4. **S5.4** Buyout cash ledger router (M, after 0016)
5. **S5.5** Reminder scheduler (L, blocked by D8 — SMTP config)
6. **S5.6** Verifier bundle PDF generator (L, after E1 pdf_renderer + after 0014/0015 from E4)
7. **S5.7** Frontend ROS export UI (M, after S5.2)
8. **S5.8** Frontend reminders dashboard (M, after S5.5)
9. **S5.9** Frontend buyout entry (M, after S5.4)

**Parallelizable work:** Migrations 0016/0017/0018 are independent of S5.1 ROS schema. Frontend tracks pair 1:1 with their backend predecessor.

**Blockers / decisions needed:**

- **D7** — fetch ROS schema (blocks S5.1)
- **D8** — SMTP config + secrets (blocks S5.5)

**Exit criteria:**

- ROS export idempotent + versioned (`ros_exports` table)
- Buyout cash ledger functional
- Reminder scheduler running + first reminder seeded for 15-Sep obligation deadline
- Verifier bundle ZIP generator produces deterministic SHA-256
- Frontend pages live for all four flows

---

### Sprint 7 — RTFO Phase 4 Annex D + Carbon Calculator (2026-08-08 → 2026-09-04)

**Goal:** Implement Annex D counterfactual methodology in code for RCF flow + Carbon Calculator import/export + 65% threshold enforcement in ledger.

**Critical path:**

1. **S6.1** Annex D methodology spec doc (M, blocked by D9)
2. **S6.2** Migration 0019 emission_factors + seed (M)
3. **S6.3** Migration 0020 annex_d_inputs (S, after 0019)
4. **S6.4** Service `ghg_annex_d.py` pure function (L, after spec)
5. **S6.5** Endpoint `POST /ghg/annex-d/compute` (M, after S6.4)
6. **S6.6** Carbon Calculator import/export (L, blocked by D10 — API vs CSV)
7. **S6.7** 65% threshold enforcement in ledger (M, after S6.5)
8. **S6.8** Frontend Annex D worksheet (XL — flag for split if estimate slips)

**Parallelizable work:** S6.2 + S6.3 migrations can land before spec doc finalizes. S6.6 Carbon Calculator is independent until ledger threshold integration.

**Blockers / decisions needed:**

- **D9** — Annex D methodology version target (blocks S6.1)
- **D10** — Carbon Calculator availability API vs CSV (blocks S6.6)

**Exit criteria:**

- Annex D formula unit-tested with sample DfT data
- Compute endpoint idempotent + advisory 422 below 65% saving
- Carbon Calculator roundtrip verified
- 65% threshold enforces 409 on `POST /rtfc-batches` unless admin override (audit logged)
- Frontend worksheet deployed

---

## Open decisions blocking sprints (D1-D10 from blueprint)

| # | Decision | Owner | Blocks | Target | Sprint impact |
|---|----------|-------|--------|--------|---------------|
| D1 | DfT extension confirmation: scope (Jan 2025 only), exact deadline 21 May 23:59 UK | Crown Oil → DfT contact | E1 baseline assumption | Day 1 EOD | Sprint 3 |
| D2 | Persist `litres_eu`/`litres_plus` as physical columns on `daily_production`? | Team ingest + Crown Oil + DfT preference | S1.1, conditional migration 0007 | Day 1 | Sprint 3 |
| D3 | Definitive supplier-to-collecting-point mapping for Jan 2025 reclassification | OisteBio | S1.7 migration 0006 | Day 1-2 | Sprint 3 |
| D4 | Crown Oil contract basis: physical segregated vs mass balance | Crown Oil | S4.1 off_takers seed | Post Crown Oil meeting | Sprint 5 |
| D5 | ELT designated by LCF Delivery Unit as RCF-eligible feedstock | OisteBio + Crown Oil → DfT LCF Unit | E4 RTFC assignment in practice (not schema) | Parallel to Jan 2025 bundle | Sprint 5 |
| D6 | RTFO-recognised verifier identification for DEV-P100 | Crown Oil → verifier search | S4.2 verifier seed + S5.6 bundle scope | Pre E4 start | Sprint 5 |
| D7 | ROS schema fetch (DfT API or downloadable doc) | Team ingest | S5.1 | Pre E5 start | Sprint 6 |
| D8 | SMTP config for reminder emails | Client + DevOps | S5.5 reminder scheduler | Pre E5 start | Sprint 6 |
| D9 | Annex D methodology version target (essential guide rev) | Team ingest + Crown Oil | S6.1 | Pre E6 start | Sprint 7 |
| D10 | Carbon Calculator availability: API vs CSV-only | DfT contact | S6.6 | Pre E6 start | Sprint 7 |

**Sequencing read:** D1/D2/D3 are emergent and resolvable in-sprint. D4/D5/D6 cluster pre-Sprint 5 and represent the hardest external dependencies — they need explicit Crown Oil + DfT engagement well before 2026-06-13. D7/D8 are tractable internal work. D9/D10 follow naturally once E5 lands.

---

## PM notes

### Velocity sanity check — does E1+E2 fit in 7 days?

**E1: 18 stories over 7 days = high but doable.** The 18 stories are mostly S (small) and M (medium); only S1.4, S1.7, S1.12, S1.15, S1.17 are M+ with real engineering risk. Critical path is sequential per-day (Day 1 → Day 7), but each day contains 2-4 stories most of which can be drafted-and-iterated rather than fully sequential. The constraint is **time, not engineer-days** — most stories are 2-8 hours of focused work, but they must land in the right sequence (PDF service → endpoint → bundle file → audit). One full-time backend engineer + one ops/document owner (Crown Oil for cover letter, OisteBio for supplier data + ANLA copies) covers the load IF D1/D2/D3 resolve Day 1.

**E2: 11 stories with the codebase already in flight.** S2.1-S2.10 are "verify-and-close" checkpoints against existing code (the architect explicitly says "state live" for each story — most already exist under `landing/src/app/app/`). S2.11 is the DoD + smoke test gate. One frontend dev part-time over 7 days closes E2 if no major regressions surface during S2.11. **Realistic risk:** smoke deploy on `oistebio.usenexos.com` may surface JWT_SECRET drift or middleware path issues (architect flagged) — budget 4-8h buffer Day 6 or Day 7 AM.

**Combined verdict:** **Feasible but tight.** Recommend declaring Day 7 frozen for E1 submission only — push E2 closure to Day 6 EOD so S2.11 smoke test does not compete with bundle upload on the same day. If E2 slips past Day 6, S2.11 can move to Sprint 4 since it does not block the regulatory submission.

### D1-D10 → sprint blocking map

- **Sprint 3 blockers (must resolve Day 1):** D1, D2, D3
- **Sprint 5 blockers (must resolve by 2026-06-12):** D4, D5, D6 — these are the **biggest external risk** in the plan. Recommend the orchestrator (you, in next step) opens a separate "client-decisions" tracking issue in Plane immediately so D4/D5/D6 do not silently slip.
- **Sprint 6 blockers (must resolve by 2026-07-10):** D7, D8
- **Sprint 7 blockers (must resolve by 2026-08-07):** D9, D10

### Stories to consider splitting before Plane creation

- **S6.8 Frontend Annex D worksheet (XL)** — the architect explicitly labels XL and notes "to split". Recommend pre-Plane-creation split into two stories: `S6.8a — Annex D worksheet form skeleton + state` and `S6.8b — Live compute preview + persist`. I have **left it as one story in the JSON payload** so the orchestrator can decide; this is the single biggest "should we split" judgment call.
- **S1.12 Cover letter + evidence index** — spans Day 4-6 and three sub-deliverables (cover v0/v1/v2 + evidence index). Architect kept it as one story; recommend keeping it monolithic in Plane since the work is owned outside the engineering team (Crown Oil legal + ops); splitting would create false granularity.
- **S5.6 Verifier bundle PDF generator (L)** — depends on pdf_renderer from E1 AND on rtfc_batches/events tables from E4. The cross-epic dependency is real; flag for the orchestrator so the `_blocked_by` array spans epics correctly.

### Stories to consider merging

None. The architect's granularity is reasonable. Two candidates I rejected:

- **S2.1 (shadcn primitives) + S2.2 (api client)** — could merge as "Sprint 3 baseline setup", but keeping them split preserves traceability against the original `docs/sprint-3-frontend.md` numbering.
- **S4.6 (off-takers router) + S4.7 (verifiers router)** — both M, both CRUD pattern. Merging saves nothing real because they touch different files and models.

### Pushback items for the architect

1. **E2 S2.x story count (11) exceeds the original `docs/sprint-3-frontend.md` story count (10).** The architect added **S2.11 DoD verification + deploy smoke test** as a "nuova" (new) story. This is a sensible addition (the original sprint-3-frontend.md DoD §5 is a checklist, not a tracked issue), but the new story has no acceptance-criteria-as-test-cases — recommend the orchestrator have the architect tighten S2.11 to a concrete pass/fail (e.g. "Playwright headless login on staging passes; `next build` exit 0; `next lint` exit 0").
2. **CLAUDE.md drift.** Architect explicitly notes in §0 that CLAUDE.md is wrong on migration count (claims 8, reality 5) and next migration prefix (claims `0009_`, reality `0006_`). Architect did NOT add a story to fix CLAUDE.md. Recommend the orchestrator add a tiny housekeeping story in Sprint 3 or Sprint 4 — I have NOT added it to the JSON to keep the count clean at 68, but flag for reviewer.
3. **Migration 0007 (litres persistence) is conditional on D2.** Architect treats this as "decision tracked, migration written if needed". The JSON payload reflects this — S1.1 is the decision, migration creation is implied as conditional work within S1.1 rather than a separate story. If D2 resolves "persist", the orchestrator may need to add a follow-up story for the actual migration; this is not a blocker but worth flagging.
4. **Cross-epic dependency S5.6 → E1 pdf_renderer + E4 batches.** The blueprint mentions extending `pdf_renderer` from E1 in S5.6. The dependency is real but easy to lose track of — orchestrator should ensure `_blocked_by` on S5.6 references both `E1-S1.3` and `E4-S4.4`.
5. **Architect did NOT split S6.8** despite labeling it XL. Already covered above.
6. **`docs/agentos-context.md` is stale.** Architect flags 5 inconsistencies in §0 between source docs (CLAUDE.md, agentos-context.md, BLUEPRINT.md). Recommend Sprint 4 or Sprint 5 includes a doc-refresh story; not in JSON to preserve count.

### Inconsistencies between blueprint and source docs (not resolved by me)

- **`docs/sprint-3-frontend.md` Definition of Done §5** says "Tutti i 10 issue chiusi in Plane" — but the architect's E2 has **11 stories** (adding S2.11). The DoD will need to be updated to 11 once issues are created. Flagging, not resolving.
- **Action plan `dft-action-plan-2026-05.md` Timeline §4 (Day 30 of window = 2026-06-13)** and blueprint timeline (Day 7 = 2026-05-21) describe **two different submission deadlines**. The action plan v3 assumes a 30-day extension to 13 June; the blueprint assumes a 7-day immediate submission on 21 May. The architect's blueprint reflects the **shorter timeline (5wd = "five working days")** — this appears to be a more recent decision. **Decision D1 must clarify** which timeline is in effect; the JSON payload assumes the 7-day timeline per the blueprint.
- **`docs/dft-action-plan-2026-05.md` §5** refers to `0005_supplier_rectification.py`; the blueprint refers to `0006_supplier_rectification_jan2025.py` (because migration `0005_production_densities` already exists in current repo). Blueprint is correct on actual numbering.

---

## Next steps for the orchestrator (you)

1. Review `plane-issue-payloads.json` for accuracy on `_blocked_by` cross-references and priority mapping.
2. Decide whether to split S6.8 pre-creation.
3. Decide whether to add CLAUDE.md fix story and docs-refresh story (would push count to 70).
4. Create modules (epics) in Plane: `e1-5wd-track-a-submission-jan2025`, `e2-sprint3-frontend-completion`, `e3-rtfo-phase1-prep-readonly`, `e4-rtfo-phase2-ledger`, `e5-rtfo-phase3-reporting-automation`, `e6-rtfo-phase4-ghg-annex-d-automation`.
5. POST issues in batch; capture issue IDs back into a `_tmp_id → real_id` map.
6. PATCH `relations` to set `blocked_by` per `_blocked_by` arrays.
7. Move E1 + E2 issues to `Todo` state (5wd window is live).
8. Surface D1/D2/D3 to client TODAY before EOD Day 1.
