# DFT-C1 — N9 SCHEME-? root-cause investigation

**Round-3 internal audit** — Phase 1 Step 4
**Date:** 2026-05-26
**Status:** investigation closed; classification recorded per cert.
**Blocking decision:** Paolo confirmation required before any
`certificates.scheme` mutation.

---

## 1. Scope

Five `certificates` rows where `scheme_pdf_detected` (parsed from the
PDF first page) disagrees with `scheme` (the DB field used by the DFT
backend and verifier-facing UI):

| cert_number | DB `scheme` | `scheme_pdf_detected` |
|---|---|---|
| `CO222-00000026` | ISCC EU | ISCC PLUS |
| `CO222-00000027` | ISCC EU | ISCC PLUS |
| `US201-120372025` | ISCC EU | ISCC PLUS |
| `US201-138762025` | ISCC EU | ISCC PLUS |
| `US201-158772025` | ISCC EU | ISCC PLUS |

The PDF files live at `data/certificates/supplier-q3/<cert>_<SUPPLIER>.pdf`
(bind-mounted into the backend container as `/data/certificates/supplier-q3/`).

The watchdog (`backend/scripts/cert_flag_watchdog.py`, Step 3) carries
these five cert numbers as the **expected** scheme-drift baseline, so
this investigation is what the watchdog expects to resolve before the
baseline is re-stated to zero.

---

## 2. Method

1. Extracted page-1 text from each PDF with `pypdf 6.12.1`
   (`/tmp/extract_cert_first_page.py`; output saved to
   `/tmp/audit_step_76/<cert>_p1.txt`).
2. Located every line on page 1 matching the regex
   `\bISCC\s*(EU|PLUS|CORSIA)\b` (case-insensitive).
3. Compared the literal scheme string against the DB `scheme` value.
4. Quoted the verbatim "complies with the requirements of the
   certification system X" sentence to remove ambiguity (some PDFs
   carry the scheme name in multiple places — header, certificate
   number prefix, body sentence, footer; only the body sentence is
   the legal declaration).
5. Cross-referenced each cert against `daily_inputs.certificate_id`
   and `supplier_certificates.certificate_id` to scope the
   downstream impact of any future scheme correction.

The investigation is read-only. **No writes were performed against
`certificates`, `daily_inputs`, or `supplier_certificates`.**

---

## 3. Per-cert findings

### 3.1 `CO222-00000026` — LITOPLAS SA (Colombia)

- **Page-1 header (verbatim):** `ISCC PLUS Certificate`
- **Certificate number on PDF:** `ISCC-PLUS-Cert-CO222-00000026`
- **Body legal declaration (verbatim):**
  > `complies with the requirements of the certification system ISCC PLUS`
- **Issuing body:** KIWA COLOMBIA S.A.S.
- **Validity (PDF):** 15.10.2024 → 14.10.2025
- **Issued/expires in DB:** 2024-10-15 / 2025-10-14 ✓
- **CoC option:** Mass Balance
- **Downstream links:** 35 `daily_inputs` rows; 3 supplier links
  (multi-supplier — also referenced by binding ECOPETROL / others
  per existing AUDIT-MISMATCH note).
- **Classification: (b)** — PDF really is ISCC PLUS; DB is wrong.
- **Co-occurrence:** this cert also carries an `AUDIT-MISMATCH` note
  (the `LITOPLAS` PDF intestation vs binding to additional suppliers
  — handled separately, NOT in scope of this Step 4 investigation).

### 3.2 `CO222-00000027` — Esenttia S.A. (Colombia)

- **Page-1 header (verbatim):** `ISCC PLUS Certificate`
- **Certificate number on PDF:** `ISCC-PLUS-Cert-CO222-00000027`
- **Body legal declaration (verbatim):**
  > `complies with the requirements of the certification system ISCC PLUS`
- **Issuing body:** KIWA COLOMBIA S.A.S.
- **Validity (PDF):** 17.10.2024 → 16.10.2025
- **Issued/expires in DB:** 2024-10-17 / 2025-10-16 ✓
- **CoC option:** Mass Balance
- **Downstream links:** 169 `daily_inputs` rows; 2 supplier links.
- **Classification: (b)** — PDF really is ISCC PLUS; DB is wrong.

### 3.3 `US201-120372025` — Bolder Industries (USA)

- **Page-1 header (verbatim):** `ISCC PLUS Certificate`
- **Certificate number on PDF:** `ISCC-PLUS-Cert-US201-120372025`
- **Body legal declaration (verbatim):**
  > `complies with the requirements of the certification system ISCC PLUS`
- **Issuing body:** SCS Global Services (Emeryville, CA)
- **Validity (PDF):** 04.04.2025 → 03.04.2026
- **Issued/expires in DB:** 2025-04-04 / 2026-04-03 ✓
- **CoC option:** Mass Balance
- **Downstream links:** 113 `daily_inputs` rows; 1 supplier link.
- **Classification: (b)** — PDF really is ISCC PLUS; DB is wrong.

### 3.4 `US201-138762025` — Kal Tire Recycling Chile (Chile)

- **Page-1 header (verbatim):** `ISCC PLUS Certificate`
- **Certificate number on PDF:** `ISCC-PLUS-Cert-US201-138762025`
- **Body legal declaration (verbatim):**
  > `complies with the requirements of the certification system ISCC PLUS`
- **Issuing body:** SCS Global Services (Emeryville, CA)
- **Validity (PDF):** 18.05.2025 → 17.05.2026
- **Issued/expires in DB:** 2025-05-18 / 2026-05-17 ✓
- **CoC option:** Mass Balance
- **Downstream links:** 189 `daily_inputs` rows; 1 supplier link.
- **Classification: (b)** — PDF really is ISCC PLUS; DB is wrong.

### 3.5 `US201-158772025` — Efficien Technology LLC (USA)

- **Page-1 header (verbatim):** `ISCC PLUS Certificate`
- **Certificate number on PDF:** `ISCC-PLUS-Cert-US201-158772025`
- **Body legal declaration (verbatim):**
  > `complies with the requirements of the certification system ISCC PLUS`
- **Issuing body:** SCS Global Services (Emeryville, CA)
- **Validity (PDF):** 26.01.2025 → 25.01.2026
- **Issued/expires in DB:** 2025-01-26 / 2026-01-25 ✓
- **CoC option:** Mass Balance
- **Downstream links:** 393 `daily_inputs` rows; 1 supplier link.
- **Classification: (b)** — PDF really is ISCC PLUS; DB is wrong.

---

## 4. Root cause

The PDFs are unambiguous. Every page-1 declaration carries the literal
phrase `complies with the requirements of the certification system
ISCC PLUS`. The certificate-number prefix `ISCC-PLUS-Cert-` confirms
the issuance scheme.

The DB column `certificates.scheme` was seeded with the default
value `'ISCC EU'` (the column default per migration; see
`certificates.scheme` column definition `DEFAULT 'ISCC EU'`).
The supplier-cert backfill that populated these five rows did not
override the default with the parsed PDF scheme — the parser added
`scheme_pdf_detected` later (migration `0029` / `backfill_cert_scope`),
which is precisely the divergence the watchdog now tracks.

**Root cause classification:** (b) for all 5 — PDF really is ISCC
PLUS; DB column carries the default `'ISCC EU'` instead of the parsed
value.

The alternative outcome (a) — parser misread — is excluded because
five independent PDFs from two different certification bodies (KIWA
Colombia and SCS Global Services) all carry the literal phrase, and
the parsed `scheme_pdf_detected = 'ISCC PLUS'` matches the PDF text
exactly.

The alternative outcome (c) — cert legacy mislabeled at issuance —
is excluded because the issuance is what the PDF declares; the
mislabel is purely in the DFT DB row, not in the PDF.

---

## 5. Downstream impact of any future correction

A switch of `scheme` from `ISCC EU` to `ISCC PLUS` on these 5 certs
would propagate to:

- **899 `daily_inputs` rows** (35 + 169 + 113 + 189 + 393) that cite
  one of the 5 certs as `certificate_id`.
- **8 `supplier_certificates` links** across the affected suppliers
  (LITOPLAS, Esenttia, Bolder, Kal Tire, Efficien Technology, plus
  the multi-supplier binding on CO222-00000026).
- **The DFT-C1 RTFO-310825 bundle** trail CSV, which (if it cites
  the `scheme` field of these certs) currently surfaces them as
  `ISCC EU` evidence — would need a re-render to reflect the
  corrected scheme.
- **The verifier-facing UI** (now hidden per N4 closure, but the
  underlying data is queryable). Crown Oil's intermediaries, if
  they query the cert-flag dimensions, would see a fresh state.

---

## 6. Compliance question for Paolo (BLOCKING)

The investigation closes with a binary question that requires
written confirmation **before any `certificates.scheme` mutation**:

> The five certs `CO222-00000026`, `CO222-00000027`, `US201-120372025`,
> `US201-138762025`, `US201-158772025` are physically issued under
> the **ISCC PLUS** scheme. The DFT bundle (RTFO-310825 → Crown Oil)
> currently surfaces them under the column value `scheme = 'ISCC EU'`.
>
> Question to Paolo: **was the ISCC PLUS certification accepted as
> equivalent evidence in the bundle that was handed to Crown Oil
> for the Q3 2025 consignment (DEL-CRW-2025-2), or were these
> suppliers expected to provide ISCC EU certificates that simply
> have not been collected?**
>
> The two possible resolutions:
>
> 1. **PLUS-accepted-as-PLUS:** Crown Oil and the UK RTFO accepted
>    these as PLUS certificates. Action: propose data-only migration
>    `0036_cert_scheme_correction.py` to update `scheme` from
>    `ISCC EU` to `ISCC PLUS` on the 5 cert rows. Update the
>    watchdog baseline (`EXPECTED_SCHEME_DRIFT_COUNT = 0`) in the
>    same commit. NO change to `daily_inputs` (the binding by id
>    stays).
> 2. **EU-was-expected:** the bundle was supposed to ride on ISCC EU
>    evidence for these suppliers. Action: request ISCC EU
>    certificates from each of the 5 suppliers (LITOPLAS, Esenttia,
>    Bolder, Kal Tire, Efficien Technology), backfill them as new
>    cert rows, soft-deprecate the PLUS certs (do NOT hard-delete —
>    ISCC EU audit safety + project soft-delete invariant), re-point
>    the affected `daily_inputs.certificate_id` values to the new
>    EU certs.
>
> Both paths preserve the historical PDF artefacts on disk and the
> immutable audit trail. **Path 2 is strictly larger work than path
> 1** (cert collection from each supplier + 899 row re-pointing) so
> path 1 is the cheaper resolution if Crown Oil accepts PLUS.

This question is bundled into Step 7 (F0-A..G batched client
questionnaire) as a new row F0-H, so Paolo only sees the question
once.

---

## 7. Provenance

- Extraction script: `/tmp/extract_cert_first_page.py` (transient).
- Raw page-1 text: `/tmp/audit_step_76/<cert>_p1.txt` (one file per
  cert). NOT committed — derived data, regenerable from
  `data/certificates/supplier-q3/<cert>_<SUPPLIER>.pdf`.
- TSV summary: `/tmp/audit_step_76/_summary.tsv` (transient).
- Mini-audit binary criterion (plan §10.3 for #76): "each cert
  classified (a / b / c) in the report". **PASS** — five-out-of-five
  classified as (b). Artefact: this document.

---

## 8. Sign-off

- Investigation executed: 2026-05-26 by Claude Opus 4.7 (1M context)
  agent under the Round-3 binding action plan.
- No DB writes performed.
- Question for Paolo recorded in Step 7 (F0-H).
- Watchdog (Step 3) baseline unchanged: still expects these 5 certs
  on the scheme-drift list. Baseline mutation deferred to the commit
  that closes Paolo's answer.

— end of investigation —
