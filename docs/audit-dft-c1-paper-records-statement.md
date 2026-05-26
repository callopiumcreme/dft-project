# Statement — Paper-records retention & UI rendering disclosure

**Subject consignment**: `DEL-CRW-2025-2` (576,270 kg DEV-P100, Crown Oil UK,
Q3 2025) and broader Feb-Aug 2025 redistribution window

**Issuer**: OisteBio GmbH (CHE-234.625.162), Oberneuhofstrasse 5, 6340 Baar,
Switzerland
**Signatory**: Paolo Ughetti, Geschäftsführer
**Date**: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
**Purpose**: provide audit-grade disclosure of (a) physical paper-record
retention for weighbridge tickets and eRSV documents covering the redistribution
window, and (b) the nature of on-screen renderings shown in OisteBio's internal
DFT tracking application.

---

## 1. Scope

This statement applies to **all feedstock deliveries** to OisteBio Pyrolysis
Plant (Girardot, Colombia) for the period:

> **2025-02-01 → 2025-08-31 (Feb-Aug 2025 redistribution window)**

This period was subject to migration `0017` of the DFT tracking system
(commit reference available on request), which performed a backfill /
redistribution of eRSV identifiers following an internal compliance review.

The window covers **7 supplier categories**:

| Code     | Holder                              | ISCC framework               |
|----------|-------------------------------------|------------------------------|
| ESENTTIA | ESENTTIA SA                         | ISCC EU `CO222-00000027`     |
| LITOPLAS | LITOPLAS SA                         | ISCC EU `CO222-00000026`     |
| BIOWASTE | BIOWASTE Sp. z o.o.                 | ISCC EU `PL21990602701`      |
| EFFICIEN | EFFICIEN TECHNOLOGY LLC             | ISCC EU `US201-158772025`    |
| KALTIRE  | KAL TIRE RECYCLING CHILE            | ISCC EU `US201-138762025`    |
| BOLDER   | BOLDER INDUSTRIES                   | ISCC EU `US201-120372025`    |
| PYRCOM   | PYRCOM SAS                          | ISCC EU `ES216-20249051`     |
| LE5TON   | aggregated dealers ≤5 t/dealer/month | ISCC self-declaration (SD)  |

---

## 2. Paper-records retention

### 2.1 Weighbridge tickets

Every feedstock delivery to OisteBio Girardot is weighed on the on-site
weighbridge operated by **Zuniga Martinez S.A.S.** (the "báscula"). For
every delivery a paper ticket is issued recording at minimum:

- Date and time of weighing
- Gross weight, tare weight, net weight (kg)
- Truck plate (placa)
- Driver name and identity number (cédula)
- Supplier / consignor name (for ISCC-certified suppliers: certificate
  reference; for `LE5TON`: dealer name and ID)
- Báscula operator (PESADO POR)

OisteBio confirms that paper tickets for the period 2025-02-01 → 2025-08-31
are **retained in physical form** at OisteBio Girardot Pyrolysis Plant
(planta) under Colombian commercial-records retention rules (Código de
Comercio, art. 60: minimum 10 years from issuance).

**Sample availability**: scanned copies of representative paper tickets can
be provided to a designated verifier within **forty-eight (48) hours** of a
written request, subject to ordinary cross-border data-transfer formalities.

### 2.2 eRSV documents

For the Feb-Aug 2025 redistribution window, original (pre-redistribution)
eRSV paper documents were reassigned to the eRSV numbers reflected in the
DFT tracking system following the migration referenced above. The
**original physical eRSV documents** issued prior to redistribution are
**retained at OisteBio Girardot** under the same retention policy described
in §2.1, alongside the post-redistribution eRSV reissues where applicable.

The single category **without** eRSV documents is `LE5TON` — small dealers
delivering at or below 5 tonnes per dealer per month, treated under the
ISCC EU **self-declaration regime** (suppliers below the volume threshold
for which a full eRSV chain is required). For LE5TON, the weighbridge
ticket (§2.1) and the self-declaration record held by the dealer constitute
the primary documentary evidence.

### 2.3 January 2025

Deliveries dated within **January 2025** are NOT covered by the
redistribution. Original eRSV and weighbridge documents for January 2025
are archived separately and are considered "frozen" for audit purposes;
this statement does not modify their status.

---

## 3. On-screen rendering disclosure

OisteBio operates an internal tracking application ("DFT") which provides
authorised personnel and, on request, verifiers with on-screen views of
weighbridge tickets and eRSV documents covering the Feb-Aug 2025
redistribution window.

These on-screen views are produced by a deterministic re-rendering process
keyed by stable identifiers (entry date, delivery position-in-day,
supplier code). The renderer populates personal-data fields (driver name,
cédula, vehicle plate, transport company, signature scrawls, báscula
operator name, hora de salida) using **deterministic placeholder values
drawn from plausible Colombian-context pools**.

OisteBio explicitly discloses that:

1. **These on-screen personal-data fields are placeholder representations**
   used for tracking-system display only. They are seeded such that the
   same delivery always renders the same placeholder values across
   re-renders.
2. **These placeholder fields are NOT to be treated as source-of-truth**
   for the purposes of any audit, verification, customs, or regulatory
   process.
3. **The source-of-truth records** for driver name, cédula, vehicle plate,
   báscula operator, signatures, and hora de salida are the **paper
   records** retained at OisteBio Girardot under §2.1 / §2.2.
4. The reason for placeholder rendering is that the underlying personal
   data (driver / vehicle / signature) **was not captured in digital form**
   at the time of the original deliveries during the Feb-Aug 2025 window;
   capture was paper-only.
5. The DFT application **clearly labels** on-screen ticket and eRSV
   renderings as such, with a visible banner referencing this statement
   (see §4 below).

Aggregate fields that ARE source-of-truth in the DFT application (and
therefore valid evidence) include:

- entry date and time of weighing
- supplier identity (ISCC certificate reference where applicable)
- net weight in kilograms (gross / tare / net per row)
- inbound / outbound eRSV numbers (where present)
- material flow timestamps and aggregations
- product C14 measurements (where present)
- physical product movements (inland → ocean → UTB transload → outbound)

---

## 4. UI banner

OisteBio commits to displaying a visible banner on every on-screen
rendering of a weighbridge ticket or eRSV covering the Feb-Aug 2025
window, with text substantially in the form:

> "On-screen rendering — personal-data fields (driver, cédula, plate,
> signatures) are deterministic placeholders. Source-of-truth records are
> paper tickets retained at OisteBio Girardot weighbridge. See
> audit-dft-c1-paper-records-statement (Paolo Ughetti, OisteBio
> Geschäftsführer)."

The banner shall be displayed in a manner not easily dismissable and shall
remain in place at least until the end of the post-audit retention period.

---

## 5. Verifier access

OisteBio undertakes to:

1. Provide, on **written verifier request**, scanned copies of weighbridge
   tickets and paper eRSV documents covering any sample selected by the
   verifier, within 48 hours of request.
2. Allow, subject to ordinary site-access protocols, **physical inspection
   of paper archives** at OisteBio Girardot during normal business hours.
3. Make available the **báscula operator** (Zuniga Martinez S.A.S.) as a
   witness for any matters concerning weighbridge integrity, if reasonably
   requested by the verifier.

---

## 6. Limitations & acknowledgements

1. This statement covers the **Feb-Aug 2025 redistribution window only**.
   Periods outside this window are governed by their respective primary
   records (electronic eRSV where present from Sep 2025 onward; frozen
   originals for January 2025).
2. This statement does **not** purport to create or substitute any ISCC EU
   certification of LE5TON suppliers. LE5TON is an aggregated category
   under the ISCC self-declaration regime and is supported by individual
   dealer self-declarations retained with the weighbridge ticket archive.
3. OisteBio confirms that the placeholder rendering described in §3 has
   **not been used** in any submission to the UK Department for Transport
   (DfT), the Renewable Transport Fuel Obligation administrator, ROS, ISCC
   System, customs, or any other regulator. All such submissions are based
   on the source-of-truth records described in §2.

---

## Signature

I, **Paolo Ughetti**, Geschäftsführer and Gesellschafter of OisteBio GmbH,
having authority to bind the company, confirm that the statements above are
true and correct to the best of my knowledge.

Signed: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Name: Paolo Ughetti

Title: Geschäftsführer, OisteBio GmbH

Place: Baar, Switzerland

Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

---

**Document control**

- Reference: `audit-dft-c1-paper-records-statement`
- Linked audit pack: `RTFO-310825` (Crown Oil UK consignment
  `DEL-CRW-2025-2`)
- Related: `audit-dft-c1-evidence-matrix.md`, `audit-dft-c1-cliente-data-request.md`
- Sensitivity: confidential — distribute to DfT verifier (Deeba Rehman) and
  Crown Oil compliance contact only, under audit cover.
