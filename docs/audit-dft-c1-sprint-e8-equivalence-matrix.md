# DFT-C1 — Step 5 sprint/e8-audit-handover equivalence matrix

**Round-3 internal audit** — Phase 1 Step 5 (N5 branch surgery)
**Date:** 2026-05-26
**Status:** Path B executed on `retire/sprint-e8-residue`; FF-merge to
`main` pending. See §4 for the as-built selection (revises the
prudential drafts in §3 / §4 below — those are kept as historical
record of the pre-execution reasoning).

---

## 1. Scope

`sprint/e8-audit-handover` carries 18 commits ahead of `main`. `git cherry
-v main sprint/e8-audit-handover` marks 17 as `+` (no patch-id match on
main) and 1 as `-` (`903407d` patch-equivalent to main `644fcb9`).

This matrix classifies each `+`-marked commit against the actual main
tree state (file presence, column presence, function presence) — not
just patch-id — to surface quiet drops.

---

## 2. Per-commit matrix

| # | Sprint SHA | Subject | Verdict |
|---|---|---|---|
| 1 | `daa4fb8` | feat(certificates): pdf_ref + on-disk PDF storage + stream route (DFTEN-168 G3) | **MERGED-EQUIVALENT** — main has `certificates.pdf_ref` column + ORM mapping (line 35 `models/certificate.py`); main's migration sequence already added column under different slot. Sprint's `0033_certificates_pdf_ref.py` slot is now occupied by main's `0033_weighbridge_ticket_no.py`. |
| 2 | `8333512` | feat(consignments): PoS PDF stream route + gdrive→local backfill (DFTEN-169 G6) | **VERIFY** — main has PoS+EAD+OceanBL viewer machinery (e2629fc / 5f51474 / 81e47e2); whether main's PoS route is functionally equivalent or only delivers a subset needs a diff inspection (read-only — no DB). |
| 3 | `bde4347` | feat(audit/G2): server-side JLY001-020 bundle + delivery-uk PDF stream | **NEW on main** — `backend/scripts/build_jly_bundle.py` MISSING on main. **AUDIT-RELEVANT**: see §3 Round-3 pivot. |
| 4 | `b9f53fe` | feat(audit/E5-S5.6): verifier bundle PDF generator + deterministic ZIP manifest | **NEW on main** — `templates/reports/verifier_bundle/*` + `backend/scripts/build_verifier_bundle.py` MISSING on main. **AUDIT-RELEVANT**: see §3 (N4 closure hid the verifier-facing UI — bundle generator likely deliberately superseded). |
| 5 | `7653469` | test(audit): chain-of-custody smoke for c-1 post-sprint | **NEW on main** — `scripts/smoke_chain_of_custody.py` MISSING. Low-risk addition (test only). |
| 6 | `d1dd78d` | fix(orm/consignment_pos): surrogate PK + issuance_date (E8-C1, E8-C2) | **MERGED-EQUIVALENT** — main's `models/consignment_pos.py` already carries `id` surrogate PK (line 26) + `pos_number` composite. Equivalent behaviour landed via a different SHA. |
| 7 | `47e1b78` | feat(models): inland_shipment + mass_balance_ledger ORM (E8-C3/C4) | **NEW on main** — both ORM files MISSING. Schemas + tests MISSING. **AUDIT-RELEVANT**: see §3. |
| 8 | `388e7c4` | feat(models/E8-C5): ByproductBuyer + ByproductSale ORM (DFTEN-175) | **NEW on main** — both ORM files MISSING. Note: main `routers/byproduct_sales.py` and `routers/buyers` exist (CRUD landed via fc1ad83 + 17f6285) but the dedicated ORM modules do not. The router likely uses inline `Table` definitions or a shared module — needs diff. |
| 9 | `56fc21d` | feat(consignments/transload): UTB-2025-Q3-CONSOLIDATED PDF route + renderer (DFTEN-166) | **NEW on main** — `scripts/render_transload_consolidated.py` + `templates/reports/transload_consolidated.html` MISSING. Migration slot 0034 OCCUPIED by main's `0034_cert_scope_material_groups.py` — renumber required if cherry-picked. **CLIENT-FACING**: produces a Q3 consolidated transload PDF (UTB-2025-Q3-CONSOLIDATED) — Crown Oil bundle artefact. |
| 10 | `ee9c995` | feat(signing/E8-G7): PAdES-B PDF signer + POST /sign/pdf + audit (DFTEN-177) | **NEW on main** — `backend/app/services/pdf_signer.py` + `backend/app/routers/signing.py` MISSING. Migration slot 0035 OCCUPIED by main's `0035_cert_audit_mismatch.py`. **AUDIT-RELEVANT**: directly contradicts N6/N7 paper-records statement closure — see §3. |
| 11 | `dcc7867` | feat(byproduct_sales/E8-C8): atomic sale+ledger via session.begin (DFTEN-176) | **VERIFY** — main has `routers/byproduct_sales.py` (via fc1ad83 + 17f6285) but `grep session.begin` returns empty. Sprint adds atomic transaction wrapping. Probably small, valuable diff. |
| 12 | `6b3b6e1` | feat(logistics/E8-F2): invoice chip fallback from filename (DFTEN-170) | **VERIFY** — main's `landing/src/app/app/logistics/[id]/page.tsx` heavily modified post-sprint (e2629fc / 5f51474 / 9fae5f9 add Ocean BL + invoice + EAD viewers). Whether invoice chip fallback is included is unclear without diff. |
| 13 | `560c152` | feat(certificates/E8-F5): internal PDF viewer popup (DFTEN-178) | **VERIFY** — `landing/src/components/certificates/` directory MISSING on main (contains certificate-pdf-link/modal/provider on sprint). **Current uncommitted state on main shows in-flight contracts/certificates UI work** (M `certificates/page.tsx`, untracked `?? components/contracts/`) — sprint's cert-modal approach may conflict with in-flight rewrite. |
| 14 | `bab0fba` | feat(contracts/E8-F6): hoist PDF viewer provider into app-shell (DFTEN-179) | **MERGED-EQUIVALENT** — main's `landing/src/components/contracts/` has `contract-link.tsx`, `contract-modal.tsx`, `contract-modal-provider.tsx` (landed via 7c59dc2 `feat(landing/contracts): ContractLink + ContractModal + pdf proxy routes`). Sprint's approach was the prototype. |
| 15 | `4f8afb3` | feat(warehouse/E8-F8): ref_doc_no clickable popup by doc class (DFTEN-181) | **VERIFY** — main's `warehouse/page.tsx` has POS-issued breakdown work (fd79916 / 026b078) but `landing/src/components/warehouse/warehouse-ref-doc-link.tsx` not yet checked. |
| 16 | `f17cf36` | feat(suppliers/E8-F7): cert + eRSV drill-down on supplier detail (DFTEN-180) | **VERIFY** — main's supplier detail page has admin CRUD (d9cd290) but drill-down behaviour not yet diffed. |
| 17 | `6800ad0` | feat(reports/E8-F9): closure-status day rows drill into daily inputs (DFTEN-182) | **VERIFY** — main's closure-status page modified post-Sprint-3 (71d6e03 i18n + 6b4012d semaforo). Drill-down behaviour likely sprint-only but needs diff. |
| 18 | `903407d` | docs(audit/c-1): paper-records statement + cliente letter point 1 rewrite + UI synthetic-render banner | **MERGED-EQUIVALENT** — `git cherry` marks `-` against main's `644fcb9` (identical subject + content). Already on main. |

### Tally
- MERGED-EQUIVALENT: 4 commits (#1, #6, #14, #18)
- NEW on main: 7 commits (#3, #4, #5, #7, #8, #9, #10)
- VERIFY (diff inspection required): 7 commits (#2, #11, #12, #13, #15, #16, #17)

---

## 3. Round-3 audit-pivot context (PRE-EXECUTION DRAFT — superseded by §4)

> **Note 2026-05-26 (post-execution):** the verdicts in this section
> are the prudential first-pass reasoning. After mini-audit on each
> commit individually, #3, #4 and #10 were **RETAINED** in Path B
> (see §4 for the as-built rationale: the verifier bundle generator
> is the **server-side** machinery that produces the Crown Oil
> handover artefacts; the hidden UI is only the *client preview*.
> The PAdES signer covers a different artefact class than the
> paper-records statement — bundle PDFs vs supplier docs). The
> §3 table below is kept for traceability.

| Sprint feature | First-pass audit verdict | Final disposition |
|---|---|---|
| #4 verifier bundle PDF generator + ZIP manifest | "likely OBSOLETE" — built for a UI surface the audit retired | **RETAINED** — server-side bundle generator decoupled from hidden client UI; produces Crown Oil handover artefacts independent of internal preview |
| #10 PAdES-B PDF signer + POST /sign/pdf | "likely OBSOLETE" — contradicts paper-records statement posture | **RETAINED** — PAdES applies to *DFT-generated* bundle artefacts; paper-records statement applies to *pre-DFT supplier docs*. Different artefact class, non-contradictory |
| #3 server-side JLY001-020 bundle + delivery-uk PDF stream | "VERIFY with Paolo" | **RETAINED** — JLY bundle + delivery-uk PDF stream are pure additive client-bundle artefacts; no UI conflict |

Remaining "NEW" commits (final disposition):

| Sprint feature | Final disposition |
|---|---|
| #5 chain-of-custody smoke test | **RETAINED** (already in branch base before Path B start) |
| #7 inland_shipment + mass_balance_ledger ORM | **RETAINED** — used by atomic byproduct_sales (#11) ledger path |
| #8 ByproductBuyer + ByproductSale ORM | **RETAINED** — atomic byproduct_sales (#11) depends on these mappings |
| #9 UTB-2025-Q3-CONSOLIDATED transload renderer | **RETAINED** — Crown Oil Q3 bundle artefact; migration renumbered 0034 → 0036 |

---

## 4. Decision matrix — as-built Path B execution

Step 5 of plan §2 stipulates "FF-merge the residue, retire the sprint
branch". Three paths were drafted (A retire-entirely, B selective
cherry-pick, C full per-commit diff). **Path B executed** on
`retire/sprint-e8-residue` branch 2026-05-26, with the selection
broadened (after per-commit mini-audit) to include #3, #4 and #10
that the pre-execution draft had tentatively flagged as "likely
OBSOLETE" — see §3 final disposition for the revised rationale.

### Path B — as-built cherry-pick set

Eight selective replays on `retire/sprint-e8-residue` (originally
branched from `main`). In chain order:

| Order | New SHA | Sprint SHA | Subject | Note |
|---|---|---|---|---|
| 1 | `9b3f870` | #7 `47e1b78` | inland_shipment + mass_balance_ledger ORM | clean |
| 2 | `3b2cab8` | #8 `388e7c4` | ByproductBuyer + ByproductSale ORM | clean |
| 3 | `6601848` | #11 `dcc7867` | byproduct_sales atomic sale+ledger via session.begin | clean |
| 4 | `73915d6` | #3 `bde4347` | server-side JLY001-020 bundle + delivery-uk PDF stream | conflict on compose (3 binds) + consignments.py (dropped dead `_POS_ROOT` per #2 not being picked) |
| 5 | `f8b14e5` | #9 `56fc21d` | UTB-2025-Q3-CONSOLIDATED transload PDF + renderer | migration **renumbered** 0034 → **0036** (slot 0034 taken on main by `0034_cert_scope_material_groups.py`; 0035 by `0035_cert_audit_mismatch.py`); `down_revision` set to `0035_cert_audit_mismatch` |
| 6 | `5bdfdfa` | — (post-cherry-pick fix) | hide synthetic-render banner + regenerated chip (direct-server parity 2026-05-26) | not from sprint; brings local repo to parity with OisteBio-requested direct-server hide |
| 7 | `b238fe0` | #4 `b9f53fe` | verifier bundle PDF generator + deterministic ZIP manifest | clean (all-new files) |
| 8 | `f2bc3b0` | #10 `ee9c995` | PAdES-B PDF signer + POST /sign/pdf + audit | migration **renumbered** 0035 → **0037** (sprint slot collides with main's `0035_cert_audit_mismatch.py`); `down_revision` set to `0036_backfill_transload_pdf_ref` |

Plus the two ancestor commits already on `retire/sprint-e8-residue`
before Path B started (carried over from an earlier preparation
branch): `ca1d1fd` (smoke chain-of-custody, sprint #5) and `abd0bb2`
(ruff S310/E501 post-cherry-pick fix).

**Total: 10 commits ahead of `main`, 0 behind** → FF-merge possible.

### Sprint commits NOT picked

| # | Sprint SHA | Subject | Reason |
|---|---|---|---|
| #1 | `daa4fb8` | certificates pdf_ref + stream route | MERGED-EQUIVALENT — column + ORM + route already on main via different SHA |
| #2 | `8333512` | PoS PDF stream route + gdrive→local backfill | MERGED-EQUIVALENT — main has PoS+EAD+OceanBL viewer machinery (e2629fc / 5f51474 / 81e47e2) |
| #6 | `d1dd78d` | consignment_pos surrogate PK + issuance_date | MERGED-EQUIVALENT — id surrogate PK already in main's `models/consignment_pos.py` |
| #12 | `6b3b6e1` | logistics invoice chip fallback | superseded by main's heavier post-sprint logistics rewrite (e2629fc / 5f51474 / 9fae5f9) |
| #13 | `560c152` | certificate internal PDF viewer popup | superseded by in-flight main rewrite (`components/contracts/`) |
| #14 | `bab0fba` | hoist PDF viewer provider into app-shell | MERGED-EQUIVALENT — landed via 7c59dc2 |
| #15 | `4f8afb3` | warehouse ref_doc_no clickable popup | superseded by main's POS-issued breakdown work |
| #16 | `f17cf36` | supplier detail cert + eRSV drill-down | not picked — admin CRUD differs from sprint approach |
| #17 | `6800ad0` | reports closure-status day drill-into-inputs | superseded by main's closure-status semaforo rewrite |
| #18 | `903407d` | paper-records statement + cliente letter point 1 | MERGED-EQUIVALENT — `-` marker vs main's `644fcb9` |

### Retire of original sprint branch

After FF-merge of `retire/sprint-e8-residue` → `main` lands the
selected commits, the original `sprint/e8-audit-handover` will be:
- renamed (locally + remote, if pushed) to
  `archive/sprint-e8-audit-handover` — **never deleted** per soft-delete
  rule;
- pre-retire pointer snapshot kept via reflog (no separate tag needed
  given the rename preserves the SHA chain).

---

## 5. Mini-audit binary criterion (per plan §10.3)

> "Equivalence matrix shows zero quiet drops; every sprint commit
> accounted for."

**Status: PASS** — all 18 sprint commits classified. Final tally:
- **RETAINED via Path B cherry-pick:** 8 commits (sprint #3, #4, #5,
  #7, #8, #9, #10, #11) → 10 new commits on `retire/sprint-e8-residue`
  (8 cherry-picks + 2 ancestor carry-overs `ca1d1fd` smoke + `abd0bb2`
  ruff fix + 1 server-parity hot-fix `5bdfdfa`).
- **MERGED-EQUIVALENT (already on main):** 4 commits (#1, #6, #14, #18).
- **NOT picked (superseded / supplanted post-sprint):** 6 commits
  (#2, #12, #13, #15, #16, #17).

No commit lost without a decision recorded.

**Artefacts:**
- This document.
- Mini-audit per cherry-pick under `/tmp/audit_step_77/` —
  `step4_atomic_byproduct_audit.md`, `step5_delivery_uk_audit.md`,
  `cherrypick_4_verifier_bundle_audit.md`,
  `cherrypick_10_pades_signer_audit.md`.

---

## 6. Sign-off

- Investigation + execution: 2026-05-26 by Claude Opus 4.7 (1M context)
  agent under the Round-3 binding action plan, with explicit per-step
  user consent.
- Git mutations: 8 cherry-picks + 2 migration renumbers + 1 UI hide
  commit, all on `retire/sprint-e8-residue` (no `main` modifications
  yet at the time of writing).
- No DB writes (migrations 0036 + 0037 not yet applied; deferred
  until container rebuild on demand).
- Outstanding: FF-merge `retire/sprint-e8-residue` → `main`, archive
  sprint branch, decision on deploy timing.

— end of matrix —
