# DFT Mass-Balance Platform — User Guide for the RTFO Administrator / UK Department for Transport

**Audience:** RTFO compliance reviewer / UK DfT officer
**Access level:** Read-only (Viewer)
**Platform:** https://oistebio.usenexos.com

---

## Table of Contents

1. [What this platform is](#1-what-this-platform-is)
2. [Your access level (read-only)](#2-your-access-level-read-only)
3. [Signing in](#3-signing-in)
4. [The screen layout](#4-the-screen-layout)
5. [Dashboard](#5-dashboard)
6. [Daily Inputs](#6-daily-inputs)
7. [Daily Production](#7-daily-production)
8. [Mass Balance report](#8-mass-balance-report)
9. [By Supplier report](#9-by-supplier-report)
10. [Daily Closure report](#10-daily-closure-report)
11. [Suppliers (master data)](#11-suppliers-master-data)
12. [Certificates (master data)](#12-certificates-master-data)
13. [Contracts (master data)](#13-contracts-master-data)
14. [Document viewers (eRSV, Ticket, Contract)](#14-document-viewers)
15. [Exporting data (CSV)](#15-exporting-data-csv)
16. [A suggested review workflow](#16-a-suggested-review-workflow)
17. [Glossary](#17-glossary)
18. [Frequently asked questions](#18-frequently-asked-questions)

---

## 1. What this platform is

This platform is the mass-balance and chain-of-custody record system for the End-of-Life Tyres (ELT) feedstock stream processed at the OISTEBIO Girardot facility and for the certified pyrolysis-oil product fractions derived from it. It is operated under the ISCC certification system (ISCC EU and ISCC PLUS), using the **mass-balance** chain-of-custody methodology.

The platform lets you, as a reviewing officer, **consult and verify** — without altering anything — the complete operational and documentary record:

- the **daily quantities of feedstock received** (truck-by-truck), with supplier, weight, and the linked electronic receipt (eRSV);
- the **daily production** figures, expressed in both kilograms and litres;
- the **mass balance** of input versus output, by day and by month, with the daily **closure** percentage that measures how well input and output reconcile;
- the **breakdown of inputs by supplier**;
- the **master data**: suppliers, ISCC certificates (with their validity dates and download links), and supply contracts;
- and the underlying **documents**: eRSV receipts, weighbridge tickets, and signed contract PDFs.

Everything is designed so that the chain of custody — from feedstock reception to final product delivery to the UK customer — can be reconstructed and cross-checked at any point.

---

## 2. Your access level (read-only)

You are signed in with a **Viewer** account. This level is deliberately limited to consultation:

| You **can** | You **cannot** |
|-------------|----------------|
| Open and read every operational and master-data page | Create, edit, or delete any record |
| Open document viewers (eRSV, ticket, contract PDF) | Change suppliers, certificates, or contracts |
| Filter, search, and sort tables | Access user management |
| Export reports to CSV | Access the audit log / administrative tools |
| Download eRSV and contract PDFs | — |

The administrative sections (user management and audit log) are **not shown** in your menu and are blocked even if reached by direct link. This guarantees that nothing in the certified record can be changed during your review.

---

## 3. Signing in

1. Open **https://oistebio.usenexos.com** in any modern browser (Chrome, Edge, Firefox, Safari). You will be taken to the sign-in screen.
2. The screen shows the heading **DFT** and the note *"Mass balance — operator access"*.
3. Enter the **Email** and **Password** that were supplied to you by e-mail.
   - The e-mail field is **not** case-sensitive — upper- or lower-case makes no difference.
4. Click **Sign in**. The button briefly shows *"Verifying…"*.
5. On success you arrive at the **Dashboard**.

**Session length:** your session lasts **8 hours**, after which you simply sign in again. The login uses a secure, http-only session cookie — there is nothing to install or configure.

If you see *"Invalid credentials"*, re-check the password (it is exact/case-sensitive). If you see *"Session expired · sign in again"*, your 8-hour window has elapsed — sign in once more.

---

## 4. The screen layout

Every page shares the same frame:

- **Left sidebar** — the navigation menu, grouped into sections:
  - **(top)** Dashboard
  - **Operations** — Daily inputs · Daily production
  - **Reports** — Mass balance · By supplier · Daily closure
  - **Master data** — Suppliers · Certificates · Contracts
- **Top bar** — a breadcrumb (shows where you are) on the left, and your account menu on the right (shows your e-mail and the role **viewer**; this is where you sign out).
- **Main area** — the content of the current page.

On a phone or narrow window the sidebar collapses into a **menu button** (☰) at the top-left; tap it to open the navigation.

> The **Users** and **Audit log** entries are intentionally absent from your menu — that is expected for a Viewer account.

---

## 5. Dashboard

**Menu:** Dashboard · **URL:** `/app`

The Dashboard is your landing page and a 30-day summary of the operation. It is the quickest way to gauge overall health before drilling into detail.

**The four KPI tiles (last 30 days):**

| Tile | Meaning |
|------|---------|
| **Total input** | Sum of all feedstock received, in kilograms. |
| **Total output** | Sum of all product/output, in kilograms. |
| **Avg closure** | The average daily closure percentage (how closely input and output reconcile). The hint shows how many days had closure data. |
| **Closure alerts** | The number of days flagged as **alert** (closure gap greater than 5%). If this is above zero it turns **red** — those days warrant a closer look. |

**Input vs output trend** — a sparkline chart plotting input (solid line) against output (dashed line), one point per day for the last 30 days. It lets you see at a glance whether input and output track each other.

If the backend is briefly unreachable you may see *"Backend unreachable · partial data"* — refresh the page.

---

## 6. Daily Inputs

**Menu:** Operations → Daily inputs · **URL:** `/app/inputs`

This page lists **every individual feedstock delivery** (each truck/vehicle entry), most recent first. It is the granular reception ledger.

**Filters (top of page):**
- **From** / **To** — date range pickers.
- **Supplier** — drop-down listing every supplier as *code · name*; choose **All** for no filter.
- **Apply** to run the filter, **Reset** to clear it.

**Table columns:**

| Column | Meaning |
|--------|---------|
| **Date** | Delivery date. |
| **Time** | Delivery time (or `—`). |
| **Supplier** | Supplier *code · name*. |
| **eRSV** | The electronic receipt number — **click it to open the eRSV document** (see §14). `—` if none. |
| **TICKET** | Click **ticket** to open the weighbridge ticket (see §14). |
| **Car** | Weight received as car tyres (kg). |
| **Truck** | Weight received as truck tyres (kg). |
| **Special** | Weight received as special/other category (kg). |
| **Total kg** | Total net weight of the delivery (bold). |
| **Open** | The **→** arrow opens the full detail of that single delivery. |

**Note on volume:** the list shows the first 50 rows; narrow the date or supplier filter to see a specific window in full. The page header summarises the count, total kilograms, and date range currently displayed.

---

## 7. Daily Production

**Menu:** Operations → Daily production · **URL:** `/app/production`

This page lists production **by day**: how much feedstock was fed into the process and how much product came out, by fraction.

**Filters:** **From** / **To** date pickers, **Apply**, **Reset**.

**Table columns:**

| Column | Meaning |
|--------|---------|
| **Date** | Production day. |
| **Input kg** | Feedstock sent to production that day. |
| **EU prod** | EU-certified light fraction produced (kg) — the **DEV-P100** product. |
| **Plus** | PLUS heavy fraction produced (kg) — the **DEV-P200** product. |
| **Output EU** | EU output (kg), bold. |
| **Contract** | The contract reference the production is allocated to (or `—`). |
| **Open** | The **→** arrow opens the full production-day detail. |

The header summarises total input, total EU output, and the date range shown.

---

## 8. Mass Balance report

**Menu:** Reports → Mass balance · **URL:** `/app/reports/mass-balance`

This is the central reconciliation report: **input versus output**, viewable **by day** or **by month**, with full breakdowns. This is where the mass-balance methodology becomes visible and auditable.

**View toggle:** **Daily** / **Monthly** (top of page).

**Filters & controls:**
- A **quick month picker** for jumping to a month.
- **From** / **To** date pickers.
- **Supplier** drop-down (**All suppliers** by default).
- **Filter** to apply, **Reset** to clear (keeps the daily/monthly view).
- **Export CSV** — downloads the current report as a spreadsheet file.

**The six KPI tiles:**

| Tile | Meaning |
|------|---------|
| **Period** | Number of days (or months) in view. |
| **Total input** | Total feedstock received (kg). |
| **Total output** | Total output (kg). |
| **Total EU (L)** | Total EU product, in **litres**. |
| **Total Plus (L)** | Total PLUS product, in litres. |
| **Total prod (L)** | EU + PLUS combined, in litres. |

Litres are derived from kilograms by **density-variable conversion** (the conversion factor depends on the density of the specific stream rather than a fixed coefficient), which is why both mass and volume are reported.

### Daily view

Each day is an **expandable row**. The header line shows **Day**, **Input**, **Output total**, and **Closure %** (the closure turns **red** when the gap exceeds 5%). Click a row (the **›** arrow) to expand it.

When expanded you see:

- **Production breakdown** (kg): *Kg → production · EU prod · Plus prod · Output EU · Carbon black · Metal scrap · H2O · Syngas · Losses* — i.e. every output and co-product stream, so the entire converted mass is accounted for.
- **Volume (litres)**: *EU prod (L) · Plus prod (L) · Total prod (L)*.
- **Truck entries** — a nested table of that day's individual deliveries with columns: **Time · Supplier · Cert / Contract** (certificate number and contract code) **· eRSV · TICKET · C14** (the radiocarbon biogenic analysis reference and value %) **· Loaded** (vehicle-type badges with kg) **· Total kg · Veg % (T / M)** (theoretical / manufacturing biogenic percentage).

The **eRSV** and **TICKET** links here open the same document viewers as on the Daily Inputs page.

### Monthly view

Each month is an expandable row showing **Month**, **Input**, **Output total**, **Closure %**. Expanding it shows the same Production-breakdown and Volume tiles aggregated for the month.

---

## 9. By Supplier report

**Menu:** Reports → By supplier · **URL:** `/app/reports/by-supplier`

This report shows **how the feedstock input is distributed across suppliers**. By default it opens on the **RTFO audit window (1 February – 31 August 2025)**.

**Filters:**
- **From** / **To** date pickers, **Filter** to apply.
- **Reset to audit window** — returns to 1 Feb – 31 Aug 2025.
- **Full period** — shows the full Jan–Aug 2025 range.
- **Export CSV**.

**KPI tiles:** **Suppliers** (count) · **Total input** (kg) · **Total entries** (number of deliveries).

**Pie chart:** *Input share by supplier* — a visual of each supplier's proportion.

**Table columns:** **#** (rank) · **Code** · **Name** · **Input kg** · **% Total** · **Entries** (deliveries) · **Days** (distinct delivery days). The final **bold** row totals everything and shows **100.0%**.

A footnote on the page explains the default audit window and how aggregate suppliers are handled.

---

## 10. Daily Closure report

**Menu:** Reports → Daily closure · **URL:** `/app/reports/closure-status`

This is the **traffic-light** view of daily reconciliation. The "closure" is the percentage difference between input and output for a day; small is good.

**Filters:** **From** / **To**, **Filter**, **Reset**, **Export CSV**.

**The five status buckets** (each a clickable tile showing a count and percentage — click to filter the table to that bucket):

| Bucket | Colour | Definition |
|--------|--------|------------|
| **OK** | dark olive | closure gap ≤ 2% |
| **Warn** | light olive | gap between 2% and 5% |
| **Alert** | red | gap greater than 5% |
| **No input** | grey | no feedstock recorded that day |
| **No output** | grey | no output recorded that day |

**Table columns:** **Day · Status** (coloured dot + label) **· Input kg · Output kg · Closure %** (coloured red on alert, olive on warn). Each row carries a colour bar on its left edge matching its bucket.

Use this report to spot, and then investigate, any day whose input and output do not reconcile within tolerance. (Note: some apparent gaps in early 2025 are explained by legitimate stock carry-over between months rather than data errors.)

---

## 11. Suppliers (master data)

**Menu:** Master data → Suppliers · **URL:** `/app/suppliers`

The supplier register.

**Toggle:** **Active** (default) / **All**. **Search** box accepts code, name, or country.

**KPI tiles:** **Suppliers** (total) · **Active** · **Aggregates** (suppliers that represent a grouped/aggregate source).

**Table columns:** **Code · Name · Country · Type** (*aggregate* or *single*) **· Status** (active / inactive badge) **· Notes · Open** (**→** to the supplier detail).

---

## 12. Certificates (master data)

**Menu:** Master data → Certificates · **URL:** `/app/certificates`

The register of ISCC and other compliance certificates, with validity dates and **download links to the issuing authority**.

**Status tabs:** **All · Active · Expired · Revoked · Placeholder**, plus an *Active only* / *All (with deleted)* switch. **Search** accepts number, scheme, or notes.

**KPI tiles:** **Total · Active · Expired · Placeholder · Expiring ≤60d** (the last turns **red** if any active certificate expires within 60 days — a renewal-watch indicator).

**Table columns:**

| Column | Meaning |
|--------|---------|
| **Number** | The certificate number. For ISCC certificates this is a **clickable link (↗)** that opens the official certificate document on the ISCC system (or the direct issuer download). |
| **Scheme** | e.g. *ISCC EU*, *ISCC PLUS*. |
| **Status** | Active / expired / revoked / placeholder badge. |
| **Issued** | Issue date. |
| **Expires** | Expiry date. |
| **Suppliers** | How many suppliers are linked to this certificate. |
| **Notes** | Free-text note (hover for the full text). |
| **Open** | **→** to the certificate detail. |

This page lets you confirm, for any supplier in the chain, that a **valid ISCC Proof of Sustainability / certificate** exists and is in date, and to open the source document directly.

---

## 13. Contracts (master data)

**Menu:** Master data → Contracts · **URL:** `/app/contracts`

The register of supply contracts and committed volumes.

**Toggle:** **Active** / **All**. **Supplier** drop-down filter, **Filter**, **Reset**.

**KPI tiles:** **Contracts** (total) · **Placeholder** (count of placeholder contracts) · **Total volume** (sum of committed kg).

**Table columns:** **Code** (clickable — opens the contract PDF viewer, see §14) **· Supplier · Start · End · Volume kg · Type** (*placeholder* / *real*) **· Status · Open** (**→** to detail).

---

## 14. Document viewers

Three pop-up viewers let you inspect the underlying evidence without leaving the page. Each opens over the current screen and closes with **Close** or the **Esc** key.

### eRSV viewer

**Open it by:** clicking an **eRSV** number in *Daily Inputs* or in the *Mass Balance* daily entries.

It shows a header (**eRSV {number}**, supplier, date, total kg, and a **regenerated** badge where applicable) and a full, faithful preview of the eRSV receipt document in the body. Use **Download PDF** to save a PDF copy. The eRSV is the originating instrument of the chain of custody for each delivery.

### Ticket viewer

**Open it by:** clicking **ticket** in *Daily Inputs* or *Mass Balance*.

It shows the weighbridge ticket as a label/value table — **eRSV · Supplier · Prod** (LLANTAS or SPECIAL) **· Driver · Cédula · Plate · Transport · Hora ent. / Hora sal.** (entry/exit time) **· Peso ent. / Peso sal. / Peso neto** (gross / tare / net weight) **· Total input · Weigher** — followed by a monospace print-preview of the ticket exactly as it appears on the thermal printer. The driver, plate and transport details are consistent with the corresponding eRSV for the same delivery. **Stampa termica** ("thermal print") downloads the raw printer file; you will not normally need this for review.

### Contract viewer

**Open it by:** clicking a **contract code** in *Contracts*.

It shows the contract's date range and committed volume in the header, then the **signed contract PDF** in the body (or *"Signed PDF not available"* where none has been uploaded yet). Use **Download PDF** to save it.

---

## 15. Exporting data (CSV)

The **Mass balance**, **By supplier**, and **Daily closure** reports each have an **Export CSV** button. It downloads exactly the data currently in view (respecting your filters) as a standard spreadsheet file, suitable for your own records or for further analysis in Excel. Exporting changes nothing in the system.

---

## 16. A suggested review workflow

A practical order for a compliance review:

1. **Dashboard** — read the 30-day totals and check the **Closure alerts** tile.
2. **Daily Closure** — open the **Alert** bucket; note any days with a closure gap over 5% for investigation.
3. **Mass Balance (daily)** — expand those days; verify the full input/output breakdown and the per-delivery entries; open the **eRSV** and **Ticket** for spot-checked deliveries.
4. **By Supplier** — confirm the input distribution over the **RTFO audit window**; export CSV for your file.
5. **Certificates** — for the suppliers that matter, confirm a **valid, in-date ISCC certificate** exists and open the source document via the **↗** link; watch the **Expiring ≤60d** indicator.
6. **Contracts** — confirm a contract and committed volume exists for the relevant suppliers; open signed PDFs as needed.
7. **Export** the reports you need as CSV and sign out from the top-right account menu.

---

## 17. Glossary

| Term | Meaning |
|------|---------|
| **ELT** | End-of-Life Tyres — the feedstock processed at Girardot. |
| **eRSV** | Electronic receipt of material — the per-delivery reception document and the first node of the chain of custody. |
| **Ticket** | The weighbridge ticket for a delivery (gross/tare/net weight, driver, plate). |
| **DEV-P100** | The certified EU light pyrolysis-oil fraction (the principal certified product). |
| **DEV-P200** | The PLUS heavy fraction. |
| **Mass balance** | The chain-of-custody method where certified characteristics are credited and allocated over a period, with input/output kept quantitatively equivalent. |
| **Closure %** | The percentage difference between a day's input and output; a measure of reconciliation. |
| **C14 / Veg %** | Carbon-14 radiocarbon analysis and the resulting biogenic-content percentage attributed to the product. |
| **ISCC EU / ISCC PLUS** | The certification schemes under which the chain of custody operates. |
| **PoS** | Proof of Sustainability — the certificate evidencing a batch's sustainability characteristics. |
| **Aggregate supplier** | A single register entry representing a grouped source of feedstock. |

---

## 18. Frequently asked questions

**Can I accidentally change or delete something?**
No. Your account is read-only. There are no edit or delete controls anywhere in your interface.

**Why don't I see "Users" or "Audit log" in the menu?**
Those are administrative tools, deliberately hidden from reviewing officers. Their absence is normal and expected.

**A date filter shows nothing — is that an error?**
Usually it means there is simply no data in that exact range. Widen the dates or use **Reset**.

**The figures are in both kg and litres — which is authoritative?**
Both are reported. Kilograms are the measured mass; litres are derived using density-variable conversion. They are provided together so mass and volume can be cross-checked.

**My session stopped working.**
Sessions last 8 hours. If you see *"Session expired"*, simply sign in again with the same credentials.

**Who do I contact about the data itself?**
For questions about specific figures, certificates, or documents, contact OISTEBIO through your usual point of contact. This guide covers only how to navigate and consult the platform.
