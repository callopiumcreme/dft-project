# RTFO-310125 — Track A Submission Bundle

## Overview

| Field | Value |
|-------|-------|
| **Submission ref** | `RTFO-310125` |
| **Period covered** | 2025-01 (January 2025) |
| **Feedstock** | End-of-life tyres (ELT) |
| **Production site** | Girardot, Colombia |
| **Bundle owner** | OisteBio GmbH — Oberneuhofstrasse 5, 6340 Baar, Switzerland (MWSt CHE-234.625.162) |
| **Regulator** | UK Department for Transport (DfT) — Low Carbon Fuels (LCF) Delivery Unit |
| **Routing** | Submitted via Crown Oil UK (sole buyer / RTFO supplier of record) |
| **Scheme** | Renewable Transport Fuel Obligation (RTFO) — Track A |
| **Language** | English (regulator-facing) |

## File naming convention

All files inside this bundle must follow:

```
RTFO-310125_<seq>_<description>.<ext>
```

Where:
- `<seq>` is the two-digit folder prefix (`00`–`05`).
- `<description>` is short, lowercase, snake_case.
- `<ext>` is the file extension (`pdf`, `xlsx`, `csv`, `json`, etc.).

Examples:
- `RTFO-310125_00_cover_letter.pdf`
- `RTFO-310125_01_annex_a_mass_balance.pdf`
- `RTFO-310125_01_annex_a_mass_balance.xlsx`
- `RTFO-310125_02_ros_export.csv`
- `RTFO-310125_03_iscc_certificate_supplier_acme.pdf`
- `RTFO-310125_05_audit_trail.json`

## Folder layout

```
deliverables/RTFO-310125/
├── README.md                          # This file
├── 00_cover_letter/                   # Signed cover letter from OisteBio GmbH to UK DfT (via Crown Oil UK)
├── 01_annex_a_mass_balance/           # Annex A — Mass balance report for Jan 2025 (PDF + xlsx)
├── 02_ros_export/                     # RTFO Operating System (ROS) machine-readable export
├── 03_supplier_evidence/              # Upstream feedstock evidence
│   ├── certificates/                  # ISCC EU / PoS certificates from ELT suppliers
│   ├── contracts/                     # Supply contracts with ELT feedstock providers
│   └── ersv/                          # eRSV (electronic Recurring Sustainability Verification) per supplier
├── 04_compliance/                     # Scheme-level compliance documents
│   ├── iscc_eu_certificate/           # OisteBio's own ISCC EU certificate (chain of custody)
│   └── rtfo_pathway_declaration/      # RTFO pathway declaration for DEV-P100
├── 05_audit_trail/                    # Immutable audit log export from DFT backend
└── MANIFEST.sha256                    # SHA-256 hashes for every file in the bundle
```

## What goes where + who produces it

| Folder | Content | Producer (story) |
|--------|---------|------------------|
| `00_cover_letter/` | Signed PDF cover letter, OisteBio GmbH letterhead, addressed to UK DfT LCF Delivery Unit, c/o Crown Oil UK. States submission ref, period, feedstock, total volume DEV-P100 delivered. | **E1-S1.10** — Cover letter authoring |
| `01_annex_a_mass_balance/` | Annex A v1: monthly mass balance report (kg in / kg out / kg stock, by feedstock & by product), PDF + source xlsx. | **E1-S1.5** — Annex A v1 generator |
| `02_ros_export/` | RTFO Operating System bulk-upload CSV (per DfT ROS template) — one row per outbound DEV-P100 consignment. | **E1-S1.6** — ROS exporter |
| `03_supplier_evidence/certificates/` | ISCC EU / RedCert / equivalent sustainability certificates from each ELT feedstock supplier active in Jan 2025. | **E1-S1.7** — Supplier evidence collation |
| `03_supplier_evidence/contracts/` | Active feedstock supply contracts covering the Jan 2025 period. | **E1-S1.7** — Supplier evidence collation |
| `03_supplier_evidence/ersv/` | eRSV statements per supplier per delivery, signed. | **E1-S1.7** — Supplier evidence collation |
| `04_compliance/iscc_eu_certificate/` | OisteBio GmbH ISCC EU certificate (chain-of-custody, mass-balance method), valid for the reporting period. | **E1-S1.8** — Compliance pack |
| `04_compliance/rtfo_pathway_declaration/` | RTFO pathway declaration for DEV-P100 (refined pyrolysis oil from ELT) — GHG saving, default value vs. actual value election. | **E1-S1.8** — Compliance pack |
| `05_audit_trail/` | Append-only audit log export (JSON) from `audit_log` table — every write touching Jan 2025 data, with actor, timestamp, before/after. | **E1-S1.4** — Audit trail exporter |
| `MANIFEST.sha256` | SHA-256 hashes for every file in the bundle. Initially populated by **E1-S1.5** (Annex A v1), finalised by **E1-S1.11** (final bundle freeze). | **E1-S1.5** + **E1-S1.11** |

## Hash verification

Once the bundle is assembled, verify file integrity from the bundle root:

```bash
cd deliverables/RTFO-310125/
sha256sum -c MANIFEST.sha256
```

Every line in `MANIFEST.sha256` must report `OK`. Any `FAILED` line blocks submission.

To (re)generate the manifest (run from the bundle root, after all artifacts are in place):

```bash
cd deliverables/RTFO-310125/
{
  echo "# SHA-256 manifest for RTFO-310125 bundle — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  find . -type f \! -name 'MANIFEST.sha256' \! -name '.gitkeep' -print0 \
    | sort -z \
    | xargs -0 sha256sum
} > MANIFEST.sha256
```

## Submission workflow (recap)

1. Each story (E1-S1.4 … E1-S1.10) drops its artifact into the correct subfolder, named per convention.
2. **E1-S1.5** computes the initial manifest after Annex A is in place.
3. **E1-S1.11** performs the final freeze: regenerates `MANIFEST.sha256`, runs `sha256sum -c`, packages the bundle, and hands it to Crown Oil UK for onward transmission to UK DfT LCF Delivery Unit.
4. Submission deadline: **21–22 May 2026**.

## Governance

- Do **not** commit real client documents to this folder in `main` — only placeholders (`.gitkeep`) and generated manifests live in git.
- Real PDFs / xlsx / certificates are staged locally and packaged at freeze time.
- Original supplier document IDs must be preserved verbatim (ISCC EU audit safety rule).
