# DfT RTFC 2025 — Action Plan

**Subject:** Crown Oil 2025 RTFC application — development diesel from EoL tyres (Colombia / OisteBio pathway).
**Context:** DfT formal rejection letter received 9 March 2026 following meeting of 5 March 2026. Bundles RTFO-310125, RTFO-280225, RTFO-310325, RTFO-310725, RTFO-210825 scheduled for deletion 13 March 2026. Original ROS resubmission deadline: 14 May 2026.
**Plan effective date:** 13 May 2026.
**Plan owner:** Crown Oil (applicant) with OisteBio (producer) and digital ingest team supporting.
**Document status:** working plan, version 1. Updates committed to git as plan evolves.

---

## 1. Executive summary

DfT has rejected the 2025 pathway in full citing three categories of failure: (a) inadequate ISCC chain of custody, (b) incomplete feedstock evidence and missing production conversion logs, (c) inconsistent and incremental submissions. The Unit has, however, explicitly left a door open: a coherent resubmission may be lodged on ROS by 14 May 2026, with verification permitted after that date subject to Unit consent.

Two months have elapsed since the rejection with no formal communication to the Unit. The intervening period has been used to engage a digital ingest and audit specialist and rebuild the evidentiary base from primary source data. That work is sufficiently advanced to:

- present a fully reconciled mass-balance for at least one month of 2025 at audit standard;
- propose a defined eight-week remediation window with milestone delivery and interim checkpoint;
- commit to a single coherent submission with no incremental or retrospective evidence.

This plan defines the steps to execute the resubmission strategy. It runs on two tracks: an immediate extension request (Track A) and, in parallel, a structured remediation program (Track B) that proceeds regardless of the extension outcome and positions the pathway for 2026 forward.

---

## 2. Acceptance of DfT findings

We do not contest the rejection. For each cited deficiency we acknowledge the substance and identify the remediation:

| DfT finding | Acknowledged | Remediation track |
|---|---|---|
| ISCC chain of custody not demonstrated | Yes | Retroactive PoS from each true collecting point, bound to specific input batches in the digital ingest system. |
| Fuel not covered by valid ISCC certificates / PoSs | Yes | Cross-reference daily inputs against ISCC certificate validity periods; flag and remediate gaps before submission. |
| Feedstock records incomplete or inconsistent | Yes | Mass-balance reports generated from primary database with daily closure to zero, exported as immutable PDF with cryptographic hash. |
| Production conversion logs (kg → litres) not provided | Yes | Add `litres` column to production table; backfill from OisteBio production records; expose in mass-balance export. |
| Most feedstock providers not registered to handle tyres | Yes | Obtain Colombian regulatory authorisations (ANLA / Ministerio de Ambiente) for each true collection point, with consular legalisation and certified EN translation. |
| Submission was incremental | Yes | Single coherent body on 30 June 2026. No partial uploads. |
| Inconsistencies in production site images, capacity, start dates | Yes | Site documentation pack consolidated from authoritative source; one signed version per item. |
| Retrospective evidence | Yes | Every document submitted will pre-date the resubmission window and be independently sourced. |

---

## 3. Two-track strategy

### Track A — Extension request (immediate, low-cost, optional outcome)

Submit a formal extension request to DfT LCF Delivery Unit on 13 May 2026 asking that the 14 May 2026 ROS deadline be extended to 30 June 2026 with an interim status checkpoint on 15 June 2026.

The extension request is preceded by a courtesy telephone call to the named DfT contact on the morning of 13 May 2026 to signal intent before the written submission arrives.

The request is accompanied by an initial body of evidence (Annex A–E, see §6) demonstrating the standard at which the resubmission will be prepared.

Probability of success is uncertain. The two-month silence and the prior rejection grounds weigh against; the substantive evidence already prepared and the limited scope of the request weigh in favour. The request is sent regardless because the cost is one day and the upside is recovery of five 2025 bundles.

### Track B — Structured remediation (independent of Track A outcome)

Whether or not DfT grants an extension, the remediation work proceeds. The deliverables Track B produces are:

- functionally required for any future application under this pathway in 2026 or beyond;
- required as inputs to the Track A resubmission if the extension is granted;
- usable as foundation evidence if Crown Oil and OisteBio elect to engage an independent ISCC verifier (Bureau Veritas, SGS, DNV) for forward applications.

Track B is the value-creating work. Track A is the attempt to recover sunk 2025 applications.

---

## 4. Timeline

All dates UK time.

### Day 0 — 2026-05-13 (today)

| Time | Action | Owner |
|---|---|---|
| Morning | Phone call Crown Oil → named DfT LCF Unit contact, signal intent | Crown Oil |
| Morning–Afternoon | Generate Annex A–E from DFT digital ingest system | Ingest team |
| Afternoon | Begin supplier rectification (replace mis-classified entities) | OisteBio + ingest team |
| End of day | Email formal extension request with annexes attached, cc OisteBio compliance lead | Crown Oil |

### Day 1 — 2026-05-14 (DfT original deadline)

- **No submission on ROS.** Submitting incomplete bundles would be rejected on the same grounds as the original investigation.
- Continue supplier rectification work.
- Await DfT response.

### Days 2–4 — 2026-05-15 → 2026-05-17 (response window)

- Confirm written response from DfT.
- If extension granted: proceed Track B with binding deadline 30 June 2026.
- If extension denied: continue Track B, reframe target to 2026 forward applications.

### Week 1 — 2026-05-19 → 2026-05-25

- Contact Litoplas, Biowaste, Esenttia compliance leads.
- Formal written request for retroactive ISCC PoS covering Jan–Aug 2025.
- Confirm appointed ISCC certifier (Bureau Veritas Colombia / SGS Colombia / other) and engage timeline.
- Identify and document any feedstock providers wrongly classified in current records (see §5).
- DFT system: implement `collection_points` table; implement `litres` column in production schema.

### Week 2 — 2026-05-26 → 2026-06-01

- Receive draft retroactive PoS or follow-up on outstanding requests.
- Initiate ANLA / Ministerio de Ambiente document requests for each collecting point.
- DFT system: implement `feedstock_provider_registration` field in supplier schema.
- DFT system: implement audit-grade PDF export endpoint for mass-balance with cryptographic hash.

### Week 3 — 2026-06-02 → 2026-06-08

- Consular legalisation of Colombian documents (UK consulate, Bogotá).
- Certified English translations.
- DFT system: implement end-to-end production log generation (kg input → kg processed → litres output).
- Begin eRSV consistency reconciliation Jan–Apr 2025.

### Week 4 — 2026-06-09 → 2026-06-15 (Interim Checkpoint)

- Compile production-to-litres records for all five bundle periods.
- Generate consolidated mass-balance reports for all bundle periods.
- **Submit written interim status report to DfT on 15 June 2026** (see §7 template).

### Week 5 — 2026-06-16 → 2026-06-22

- If engaged: kick-off independent ISCC certifier pre-audit.
- Assemble final submission packages per bundle (see §8 structure).
- Generate cryptographic snapshot of database state to underwrite the evidence trail.

### Week 6 — 2026-06-23 → 2026-06-29

- Internal audit of the assembled body.
- Cross-reference: every kilogram in mass-balance ↔ ISCC PoS ↔ provider registration.
- Final formatting per ROS requirements.

### Day 30-of-window — 2026-06-30

- **Submit on ROS.** Single coherent body, all five bundles.
- Notify DfT named contact by email of submission.

### Post-submission — 2026-07 → 2026-08

- Respond promptly to DfT verification questions. Never incrementally.
- If approved: apply same standard going forward.
- If rejected: pathway closed for 2025 bundles; Track B deliverables retained for 2026 forward applications.

---

## 5. Supplier and collecting-point rectification

The current digital ingest system reflects seven supplier records: ESENTTIA, SANIMAX, LITOPLAS, CIECOGRAS, BIOWASTE, ECODIESEL (dormant), and an aggregate "≤5 TON" bucket for self-declared ISCC small batches. DfT's working understanding identifies only Litoplas, Biowaste, and Esenttia as collecting points.

A surgical reclassification is being performed today to align supplier records with the true collecting-point structure. Principles:

- **No hard delete.** Reclassified suppliers are soft-deleted with explanatory notes referencing the DfT investigation. Audit trail preserved.
- **No silent rewrite.** Every reattribution of a daily input from a wrong supplier to the correct collecting point is logged in `audit_log` with `old_values` and `new_values`.
- **Volumes preserved.** Kilogram totals per date remain unchanged. Only the attribution to the correct collecting point changes.
- **Certificates preserved.** Original ISCC certificate records are retained even when reassigned; provenance of the historical record is auditable.
- **Provenance reconstructible.** From any current state, the audit log permits reconstruction of the state immediately prior to rectification.

The migration is recorded as `0005_supplier_rectification.py` (or equivalent operational SQL) and applied locally and on the production server with verification of mass-balance closure before and after.

The output of this rectification feeds directly into Annex B (supply chain diagram) and Annex C (evidence register).

---

## 6. Initial body of evidence (annexes to extension request)

### Annex A — Sample reconciled mass-balance (July 2025)

A daily mass-balance for July 2025 generated from the OisteBio digital ingest system. Daily closure (input − production − by-products) equals zero across all 31 days. Includes per-day detail and monthly aggregate. Format: PDF, signed, with SHA-256 hash for integrity verification. This is the format in which all five bundle months will be re-presented.

### Annex B — Supply chain diagram

A diagram showing four layers: origin points (where applicable), collecting points (ISCC-certified, post-rectification), OisteBio facility (receipt and conversion), and Crown Oil (UK end supplier). Includes the ISCC PoS issued at each transfer.

### Annex C — Evidence register

A working table listing every document required for the resubmission, with current status (available, in progress, to collect), owner, and target completion date. Items already available include the digital mass-balance, the audit log, and the stock carry-over explanation. Items to be collected include retroactive ISCC PoS from each collecting point, Colombian regulatory authorisations, and OCR'd / digitised 2024 records.

### Annex D — Stock carry-over explanation (January / February 2025)

A written explanation of the apparent closure variance in January and February 2025, which represents a symmetric ±339,865 kg carry-over of feedstock stock from year-end 2024 to early 2025 inventory. The variance reconciles to zero across the two months and is reconstructible from primary source data.

### Annex E — Milestone plan

This document, summarised in tabular form for the extension request package.

---

## 7. Interim checkpoint — 15 June 2026 (template)

```
Subject: RTFO 2025 EoL Tyres Pathway — Interim Status Report (per extension agreement)

Dear [Name],

Per the agreement of [DATE], please find Crown Oil's interim status report
against the Evidence Register submitted on 13 May 2026.

Items completed since 13 May:
- [each item from Annex C marked complete, with reference]

Items in progress:
- [each item, with revised completion target if any has slipped]

Items not yet started:
- [each item, with reason and target start]

Risks and dependencies:
- [legalisation timelines, certifier availability, third-party responsiveness]

Confirmation: we remain on track for submission by 30 June 2026.

[Signed, Crown Oil]
```

---

## 8. Final submission package structure — 30 June 2026

Per bundle (five bundles total):

```
bundle_RTFO-XXXXXX/
├── 00_cover_letter.pdf                 (Crown Oil signed)
├── 01_supply_chain_diagram.pdf         (origin → collecting point → OisteBio → Crown Oil)
├── 02_mass_balance_monthly.pdf         (DFT system export, daily + monthly aggregate)
├── 03_iscc_pos_chain/
│   ├── litoplas_pos_YYYY-MM.pdf
│   ├── biowaste_pos_YYYY-MM.pdf
│   ├── esenttia_pos_YYYY-MM.pdf
│   └── oistebio_pos_to_crownoil_YYYY-MM.pdf
├── 04_feedstock_provider_authorisations/
│   ├── litoplas_anla_permit.pdf        (legalised + EN translation)
│   ├── biowaste_anla_permit.pdf
│   └── esenttia_anla_permit.pdf
├── 05_production_conversion_logs.pdf   (kg → litres, daily, signed)
├── 06_audit_trail_export.csv           (from DFT audit_log table)
├── 07_independent_audit_letter.pdf     (if ISCC certifier engaged)
└── 08_evidence_index.pdf               (cross-reference docs ↔ DfT rejection points)
```

A consolidated cover letter accompanies the five bundle packages on ROS.

---

## 9. Commitments to the Unit

Conditional on the extension being granted, Crown Oil and OisteBio commit to:

- **No further incremental submissions.** The submission on 30 June 2026 will be a single coherent body.
- **No retrospective evidence.** All evidence will pre-date the assembly window and be independently sourced.
- **Interim transparency.** A written status report will be provided on 15 June 2026.
- **Independent verification on offer.** We are prepared to engage an independent ISCC certifier to pre-audit the body if the Unit considers this useful.
- **Single point of contact.** All correspondence will route through one named Crown Oil contact to avoid the fragmented communication that contributed to the original rejection.

---

## 10. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DfT denies extension | Medium-High | High (2025 bundles lost) | Track B continues regardless; 2026 forward salvageable. |
| Colombian regulatory authorisations not obtainable in window | Medium | High | Begin requests Week 1; escalate via Colombian consulate UK if delayed. |
| Retroactive ISCC PoS not granted by certifier | Medium | High | Engage ISCC certifier formally Week 1; if refused, document refusal and submit non-ISCC chain evidence per RTFO fallback procedure. |
| 2024 handwritten records unreadable | High (known) | Medium | OCR pipeline with manual verification; if unreadable, document the limitation and submit declaratively. |
| eRSV duplicates Jan–Apr 2025 cannot be reconciled | Medium | Medium | Document the source-system limitation; provide reconciled view from primary data. |
| Internal audit (Week 6) discovers further gaps | Medium | High | Daily standups Week 5–6 to surface gaps early; defer submission rather than submit incomplete. |
| Submission rejected again | Medium | Final | Pathway closed for 2025. Retain Track B output for 2026 forward applications. |

---

## 11. Plan B — pathway 2026 forward

If 2025 bundles are not recoverable, Track B output positions the pathway for 2026 forward applications. Deliverables that have lasting value:

- A digital ingest system with daily mass-balance closure to zero, audit log, and cryptographic export — directly addresses DfT's "information quality" critique for any future application.
- A reconstructed supply chain with verified collecting points and ISCC certificate bindings — addresses the "ISCC chain of custody" critique.
- Colombian regulatory authorisations for each collecting point — addresses the "feedstock provider registration" critique.
- An offer of independent ISCC certifier pre-audit — addresses the "incremental and inconsistent submission" critique.

A 2026 application built on this foundation enters with a markedly stronger evidentiary position than the 2025 applications did.

---

## 12. Plan ownership and updates

- **Crown Oil:** applicant of record; all communication to DfT.
- **OisteBio:** evidence assembly, supplier rectification, Colombian regulatory liaison.
- **Digital ingest team:** DFT system implementation, mass-balance reports, audit trail, OCR pipeline.

This plan is committed to the repository under `docs/dft-action-plan-2026-05.md`. Updates are made via git commit with reference to the relevant section. Material changes (deadline extension granted/denied, scope adjustments, additional regulatory requirements) are reflected in a new version of this document with a changelog entry below.

---

## Changelog

- **v1 — 2026-05-13:** Initial plan committed.
