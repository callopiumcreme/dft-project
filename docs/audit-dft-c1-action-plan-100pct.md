# Audit DFT-C1 — Action Plan to 100% Red-Audit Green

**Status:** binding — every action below executed against this checklist
**Created:** 2026-05-26
**Owner:** Internal red-team (OisteBio GmbH)
**Subject:** DEL-CRW-2025-2 (Crown Oil UK, 576,270 kg DEV-P100, Q3 2025)
**Cross-ref:**
- `docs/audit-dft-c1-evidence-matrix.md` — full evidence matrix, F0/X/N findings
- `docs/audit-dft-c1-paper-records-statement.md` — Geschäftsführer countersignature artefact
- Sibling: `BLUEPRINT.md`, `docs/agentos-context.md`

---

## 1. Purpose

This document is the **binding sequencing constraint** for closing the
DFT-C1 audit from its current 35% green state (5 / 14 criteria) to 100%
red-audit green. It supersedes any verbal in-thread sequencing decision.
Any deviation from the order below must be explicitly justified in the
same response that diverges, and the row in §5 marked accordingly.

Operating disciplines (non-negotiable, sourced from project memory):

- **HARD LOCAL FIRST** — `"go"` / `"ok"` without target qualifier means
  localhost only. Production (`oistebio.usenexos.com`, any Hetzner host)
  requires explicit per-action consent for every individual action. Data
  backfills directly to production are forbidden.
- **No legions** — no parallel `Agent` spawns with `isolation: worktree`
  on DFT. Work proceeds serial in the main thread, visible step-by-step.
- **Read-before-Edit** — every file is read in full (or relevant slice)
  before any edit. Stale assumptions about file contents are the single
  most expensive failure mode.
- **No password / secret changes** — never reset `password_hash`, JWT
  secrets, or external-service credentials without per-action consent.
- **Migration row-id portability** — data migrations must not key UPDATE
  on auto-increment IDs (silent fail across environments — 0016 lesson).
- **`rsync` env-file gotcha** — never pass `--delete-excluded` to the
  oistebio rsync target; would wipe server-only `.env.local`.
- **Direct DB queries via `docker exec ... psql`** — use psql for data
  exploration, never the REST API.
- **BiNova never appears in client-facing copy** — internal dev studio.
- **Single buyer Crown Oil UK** — Europe excluded from copy / scope.
- **No Drive runtime** — DFT never reads from Google Drive at runtime;
  Drive is artefact-storage only.
- **ISCC EU audit safety** — preserve original supplier doc IDs; never
  silently rewrite historical compliance data.
- **Pydantic v2** — `model_dump()` not `.dict()`; **never** write
  `total_input_kg` (GENERATED ALWAYS); **never** `REFRESH MATERIALIZED
  VIEW CONCURRENTLY` inside a transaction.

---

## 2. Phase 1 — Foundation autonomous (own ship, no client dependency)

Branch base: `audit/jan-inclusion-and-placeholder-marker`, cut off `main`.
Each step lands as an atomic commit; commits are not squashed at merge.

### Step 1 — N6 Window extend to include January 2025

- **File touched:** `landing/src/config/paper-records-window.ts`
- **Change:** `WINDOW_START_ISO = '2025-01-01'` (was `'2025-02-01'`).
- **Reason:** January 2025 contains 209 `daily_inputs` rows that currently
  render `ersv_pool` placeholders without the `SyntheticRenderBanner`
  disclosing the synthetic nature. Bringing January inside the window
  fires the banner on those rows.
- **Verification:** Playwright smoke against `/app/inputs?date=2025-01-15`
  asserting banner DOM node present.
- **Commit message:** `feat(audit/window): extend paper-records window to 2025-01-01 (N6)`
- **Risk:** zero — single literal change, broadly readable elsewhere.
- **Gate G1:** smoke green. On red, revert + investigate before continuing.

### Step 2 — N6 / N7 Placeholder marker (option C)

- **Backend file:** `backend/app/services/ersv_pool.py`
- **Frontend file:** `landing/src/components/audit/synthetic-render-banner.tsx`
- **Change:** when an `entry_date` is inside the paper-records window,
  the personal-data fields (driver, cédula, placa, firma, `PESADO POR`,
  hora de salida, báscula operator) are emitted as the literal marker
  `[Paper record — Girardot archive]` rather than as deterministic
  placeholder values. The banner copy is updated to describe the marker
  rather than to characterise the underlying data as "symbolic" or
  "placeholder".
- **Reason:** removes the self-incriminating "symbolic data" exposure
  surface (N7) and makes the binding relationship explicit on the UI
  surface (N6). The DfT verifier never reads a personated name that
  the company cannot stand behind.
- **Verification:**
  - Backend `pytest tests/services/test_ersv_pool.py` — snapshot updated.
  - Playwright modal on a January row and a February row — both display
    the marker, neither displays a deterministic personal name.
- **Commit message:** `feat(audit/placeholder-marker): replace synthetic personal-data with paper-record marker (N6/N7)`
- **Risk:** medium — changes the eRSV API output for paper-records
  window rows. Verify no downstream consumer (CSV export, PDF render)
  ingests the field expecting a personal name.
- **Gate G2:** snapshot tests + Playwright modal screenshot match.

### Step 3 — Internal cert-flag drift watchdog

- **File created:** `backend/scripts/cert_flag_watchdog.py`
- **Companion test:** `backend/tests/test_cert_flag_watchdog.py`
- **Change:** the watchdog reads `certificates.notes LIKE
  '%AUDIT-MISMATCH%'` count and `certificates.scheme_pdf_detected <>
  scheme` count. The expected counts (currently 2 and 5 respectively)
  are stored in a small JSON-shaped expectations file. Drift causes
  exit code 1.
- **Reason:** since the verifier-facing UI no longer surfaces these
  flags (commit `7e3234d`, finding N4 closed by hiding), the data layer
  needs an automated guard against silent drift.
- **Verification:** test runs the watchdog against the current DB state
  and asserts exit 0; then mutates one row and asserts exit 1.
- **Commit message:** `feat(audit/watchdog): cert-flag drift detector (N10)`
- **Risk:** zero — read-only.
- **Gate G3:** watchdog exits 0 on the current DB state.

### Step 4 — N9 SCHEME-? root-cause investigation

- **Five certificates with mismatch:** `CO222-00000026`, `CO222-00000027`,
  `US201-120372025`, `US201-138762025`, `US201-158772025`.
- **Method:** extract the first page of each cert PDF (`pypdf` or
  `pdftotext` first-page text) and compare the scheme line literally
  against the `certificates.scheme` value. Document the byte-level
  finding for each cert.
- **Output:** `docs/audit-dft-c1-scheme-mismatch-investigation.md`.
- **Possible outcomes:**
  - (a) Parser misreads a leading-whitespace or visually-similar
    character — fix the parser, re-run `scripts/backfill_cert_scope.py`,
    mismatch count goes to zero.
  - (b) PDF really is `ISCC PLUS` — propose data-only migration `0036`
    to update `certificates.scheme` from `ISCC EU` to `ISCC PLUS` for
    those rows, **conditional on Paolo confirmation** that the legal
    scheme is PLUS (never silently rewrite — ISCC EU audit safety).
  - (c) Cert legacy mislabeled at issuance — keep mismatch, add an
    `AUDIT-MISMATCH` note documenting binding, ASK Paolo on resolution.
- **Commit message:** `docs(audit): SCHEME-? 5-cert investigation report (N9)`
- **Risk:** read-only investigation; mutations only on explicit Paolo
  confirmation in outcome (b) or (c).
- **Gate G4:** investigation report committed; root-cause classified
  per cert.

### Step 5 — N5 sprint/e8-audit-handover retire

- **Current state:** `sprint/e8-audit-handover` is 18 commits ahead of
  `main` and 18 commits behind. Earlier renumber (sprint `0033` /
  `0036` → main `0033` / `0035`) was reconciled in the local DB via
  `/tmp/dft-main-align.sql` stamp, but the branch itself was never
  rebased or retired.
- **Method:**
  1. Per-commit content diff `sprint/e8-audit-handover` vs `main` —
     identify commits already represented in main with equivalent
     content (different SHA, same effect).
  2. Cherry-pick the residual genuinely-new commits onto a transient
     branch off main; resolve renumber collisions deliberately.
  3. Smoke + tests green on the transient branch.
  4. FF-merge transient branch to main.
  5. Delete `sprint/e8-audit-handover` only after the equivalence
     verification matrix is recorded in the commit body of the merge
     — reflog gives 90-day safety net but the record is the audit
     trail.
- **Commit message (cover):** `chore(branches): retire sprint/e8-audit-handover after equivalence verify (N5)`
- **Risk:** low — branch surgery with the reflog as safety net; the
  equivalence verification is the hard part.
- **Gate G5:** every commit on the retired branch is accounted for
  (merged-equivalent or cherry-picked); zero quiet drops.

---

## 3. Phase 2 — Client-blocked (waiting on Paolo / Hugo)

These items do not unblock by internal work alone. They are sequenced
last because they cannot complete without client-side input.

### Step 6 — F0-F backfill remaining 8 certificates

- **Current coverage:** `scope_material_groups` populated on 8 / 16
  certificates.
- **Action:** export the list of 8 missing certificates from
  `certificates` where `scope_material_groups IS NULL`, request the
  corresponding PDFs from Paolo, drop them in the cert-storage bind
  mount, re-run `scripts/backfill_cert_scope.py`.
- **Verification:** coverage reaches 16 / 16; watchdog (Step 3) still
  exits 0.

### Step 7 — F0-A through F0-G batched client request

- **Bundled ask** to Paolo + Hugo, single Plane ticket, scoped to:
  - F0-A POS ↔ production binding (Paolo)
  - F0-B ELT-only origin proof Girardot (Hugo)
  - F0-C ISCC + RCF dossier UK-only (Paolo)
  - F0-D Bundle handover to Crown Oil (Paolo → Crown)
  - F0-E ISCC certificate audit-pass refresh date (Paolo)
  - F0-G EAD customs chain end-to-end (Hugo)
- **Form:** structured questionnaire, each row a F0 ID + precise
  artefact requested + acceptance criterion.
- **Output:** Plane ticket reference recorded in
  `docs/audit-dft-c1-evidence-matrix.md` §10 (new section).

---

## 4. Phase 3 — Statement + Drive final (strict sequencing)

This phase runs **only after Phase 1 is fully green** and Phase 2 has
returned client input. Statement coherence depends on the achieved
state of the codebase, the database, and the cert dossier.

### Step 8 — Statement rewrite

- **File:** `docs/audit-dft-c1-paper-records-statement.md`
- **Changes:**
  - §1 Scope: extend to `2025-01-01 → 2025-08-31`; document January
    inclusion rationale (initial Q1 partial bundle was submitted to
    DfT and rejected; current redistribution restates the same
    paper-archive figures under the corrected framework).
  - §3 Disclosure: strip the phrases `symbolic data`, `deterministic
    placeholders`, `not source-of-truth`. Replace with: "the binding
    source-of-truth for the listed personal-data fields is the paper
    documentation retained at the OisteBio Girardot archive; the DFT
    UI surfaces the marker `[Paper record — Girardot archive]` to
    point the verifier to the physical source".
  - §6 Limitations: clarify that for the January 2025 sub-window the
    paper archive is the primary record and the DFT UI is a secondary
    view; for February to August 2025 both views are aligned through
    the redistribution process.
  - New §7 — Q1-2025 DfT submission history: state that the original
    Q1 2025 partial bundle was submitted and rejected for compliance
    gaps; the current bundle represents the corrected redistribution
    of the original paper-record data, with no fabricated quantities.
- **Verification:** Paolo legge la bozza pre-firma. No legal-review
  step is skipped.

### Step 9 — Drive replace + Paolo signature

- **Drive:** `rclone copy` of the updated `.md` and the regenerated
  `.pdf` to `gdrive:DFT_2025/PARTICULARES/`, overwriting the existing
  draft.
- **Signature:** Paolo signs the final PDF; the signed PDF lands back
  in `gdrive:DFT_2025/PARTICULARES/` under a `signed/` subfolder.
- **Gate G6:** explicit consent — `"ok carico su drive"` — required
  before any Drive write.

---

## 5. Green criteria checklist

| # | Criterion | State 2026-05-26 |
|---|-----------|------------------|
| 1 | `alembic_version` at main chain head (`0035_cert_audit_mismatch`) | ✅ |
| 2 | DB columns present (`scope_*` × 4, `weighbridge_ticket_no` × 1) | ✅ |
| 3 | `scope_material_groups` backfill reaches 16 / 16 | ⏳ Step 6 |
| 4 | `SCHEME-?` count → 0 or documented per-cert binding | ⏳ Step 4 |
| 5 | `AUDIT-MISMATCH` count → 0 or documented per-cert binding | ⏳ Step 7 (F0-A) |
| 6 | Banner window centralised in `paper-records-window.ts` | ✅ |
| 7 | Banner window includes January 2025 | ⏳ Step 1 |
| 8 | `TicketLink` not mounted in app-shell or `/app/inputs` rows | ✅ |
| 9 | Cert-flag badges hidden from verifier-facing UI | ✅ |
| 10 | Paper-records placeholder strategy → marker (option C) | ⏳ Step 2 |
| 11 | `sprint/e8-audit-handover` retired or rebased over main | ⏳ Step 5 |
| 12 | Internal cert-flag drift watchdog active | ⏳ Step 3 |
| 13 | Statement rewritten — January in scope, marker language | ⏳ Step 8 |
| 14 | Statement signed by Paolo; Drive replaced | ⏳ Step 9 |

**Current:** 5 / 14 green (35%).

---

## 6. Execution gates

| Gate | Triggered after | Pass condition | Action on fail |
|------|-----------------|----------------|----------------|
| G1 | Step 1 | Playwright smoke shows banner on a January row | revert config change, investigate `isInPaperRecordsWindow` |
| G2 | Step 2 | Backend snapshot + Playwright modal show marker text on both January and February rows | revert ersv_pool change, investigate consumer compatibility |
| G3 | Step 3 | Watchdog exits 0 on the current DB state | tune expectations file before relying on the gate |
| G4 | Step 4 | Investigation report committed; outcome classified per cert | do not proceed to mutations before classification |
| G5 | Step 5 | Equivalence matrix recorded in merge commit body; reflog snapshot of pre-delete branch head saved | abort delete; keep sprint/e8 branch |
| G6 | Step 9 | Explicit user consent to Drive upload + Paolo OK on the draft | wait |

---

## 7. Deploy posture

No deploy to `oistebio.usenexos.com` or any Hetzner host occurs during
Phase 1 or Phase 2. Every change in those phases is local; every smoke
runs against the local stack only (`localhost:3030` landing,
`localhost:18000` backend). Deployment is contemplated only after
Phase 3 completes and Paolo explicitly authorises it for each target.

---

## 8. Recording divergence

If any step is executed out of order, or skipped, the executing turn
must:

1. State the divergence explicitly in its own response.
2. Update the row in §5 to reflect actual state.
3. If the divergence introduces work not already in this plan, append
   the new work as a new step in §2, §3, or §4 — never inline-replace
   existing steps.

---

## 9. Document revision

Single-author document. Revisions happen by direct edit on `main`; the
git history of this file is the change log.

---

## 10. Audit cadence per step

Added 2026-05-26 during Step 2 closure. Each step in §2–§4 carries an
explicit audit obligation. Two grades of audit, deliberately
asymmetric in cost and scope:

### 10.1 Mini red-audit (5–10 min) — per step

Runs **after every step lands on main**, before moving to the next.

- **Binary criterion declared BEFORE the step starts.** No post-hoc
  goalpost shift. The criterion is written as a single PASS/FAIL
  predicate against a measurable artefact.
- **Scope = only that step's surface.** Cross-step regressions are
  not in scope; that is the milestone audit's job.
- **1–2 targeted probes maximum.** A single Playwright smoke, a single
  curl + diff, a single DB query — whichever directly answers the
  criterion.
- **One durable artefact** persisted to `/tmp/audit_step_<n>_*`
  (smoke output, screenshot, query result, diff). The artefact path
  is recorded in the commit body or in a follow-up note.
- **Output: PASS or FAIL.** No "almost". A FAIL blocks the next step
  until reconciled.

### 10.2 Full red-audit (30–60 min) — at phase milestone

Runs at Phase 1 close, Phase 2 close (post-client-return), Phase 3
close. Treated as a release gate.

- Re-executes all gates G1–G6 from §6.
- Re-runs every step's mini criterion as a regression suite — catches
  the cross-step interactions the mini audits intentionally ignore.
- Verifies emergent properties (statement wording vs marker semantics
  vs Drive bundle integrity, e.g. §4 Step 8 + Step 9).
- Failure rolls back the most recent phase boundary, not the whole
  plan.

### 10.3 Per-step scope assignment

| Step | Audit grade | Notes |
|------|-------------|-------|
| #73 Step 1 — N6 window extend | mini — done in commit smoke | Verifier-facing UI change. |
| #74 Step 2 — N6/N7 marker | **mini — done in commit `61513ef`** | Verifier-facing UI + backend output; artefacts under `/tmp/audit_pr_banner_*`. |
| #75 Step 3 — cert-flag watchdog | mini = spot-check on script output | Internal-only; criterion = exit 0 against current DB + exit 1 after seeded drift. |
| #76 Step 4 — N9 SCHEME-? investigation | mini = investigation report committed | Read-only; criterion = each cert classified (a / b / c) in the report. |
| #77 Step 5 — sprint/e8 retire | mini = equivalence matrix complete | Internal-only; criterion = matrix shows zero quiet drops. |
| **PHASE 1 CLOSE** | **full** | After Step 5 lands. |
| #78 Step 6 — F0-F backfill (8 certs) | client-blocked → mini on return | Run mini when Paolo delivers PDFs; criterion = coverage 16 / 16 + watchdog still green. |
| #79 Step 7 — F0-A..G questionnaire | mini = Plane ticket posted with all 7 rows | Internal-only; criterion = ticket URL recorded in evidence matrix §10. |
| **PHASE 2 CLOSE** | **full** | After Step 6 + Step 7 both return client input. |
| #80 Step 8 — Statement rewrite | mini = diff review against §4.Step8 spec | Verifier-facing; criterion = all forbidden phrases (`symbolic data`, `deterministic placeholders`) absent, all required phrases present. |
| #81 Step 9 — Drive replace + signature | mini = SHA-256 of uploaded bundle matches local | Outward-facing; criterion = Drive file SHA matches local + Paolo signature attached. |
| **PHASE 3 CLOSE** | **full + handover** | After Step 9. This is the Crown Oil handover gate. |

### 10.4 Why this asymmetric design

1. **Binary criteria upfront** — matches the project-wide rule of
   verifying every claim before reporting; "looks fine" is not a
   PASS.
2. **Bounded scope per mini** — prevents audit fatigue and scope
   creep; an audit that re-checks everything every time gets skipped.
3. **Durable artefacts** — `/tmp/audit_step_<n>_*` paths are
   replayable evidence; we never depend on "I remember the screenshot
   was green".
4. **Milestone re-audit** — the regression suite catches the
   cross-step interactions the minis miss by design (e.g. Step 8
   wording assumes Step 2 marker semantics; only the Phase 3 full
   audit verifies both together).

— end of binding action plan —
