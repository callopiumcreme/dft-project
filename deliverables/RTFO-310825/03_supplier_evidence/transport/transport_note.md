# Outbound transport — Bill of Lading + arrivals tracker

**Reporting period:** 2025-01-01 to 2025-08-31
**Bundle ref:** RTFO-310825
**Last updated:** 2026-05-21

## Scope

Documents the outbound shipping leg from the OisteBio plant (Girardot, Cundinamarca — Colombia) to the off-taker Crown Oil Limited (UK) via the
Dordrecht (NL) intermediate hub. The shipping leg is operated by carrier CMA CGM (sea freight) and the NL→UK road leg by UTB BV / Crown Oil hauliers.

## Files

| File | Description |
|------|-------------|
| `BL_CMDU856254189_CARTAGENA_EXPRES_2025-06-11.pdf` | Bill of Lading — vessel CARTAGENA EXPRES, voyage 005COEN, issued 2025-06-11. 15 × 20'ISO containers DEV-P100 refined pyrolysis oil. Shipper: OISTEBIO (c/o CALTASRO GMBH). Consignee: c/o UTB BV, Dordrecht NL. |
| `BL_CMDU877254433_ISTANBUL_EXPRES_2025-07-03.pdf` | Bill of Lading — vessel ISTANBUL EXPRES, voyage 005CONU, issued 2025-07-03. Same shipper / consignee chain. |

The matching shipper-side arrivals/UK-delivery xlsx tracker (29 outbound containers ex-Cartagena ~575.7 t; 20 NL→UK road deliveries 500.41 t total, PoS refs `OISCRO-0013-25` .. `OISCRO-0032-25`) is held internally by OisteBio as a cross-check workbook and is not part of the audit-visible bundle. Auditor cross-references should rely on the two BLs above for the certified evidence chain.

## Pre-export stockpile — January to May 2025

Production from January through May 2025 was accumulated as on-site stockpile at the Girardot plant. **No Bill of Lading exists for that window** because no
outbound shipment took place — the first export to the NL hub is BL `CMDU856254189` dated 2025-06-11. The stockpile bridge is what closes the mass balance between
the per-month Annex A reports and the actual June/July shipping events.

This is the same physical inventory captured in `06_annex_d_stock_carryover/07_stock_carryover_jan_feb_2025.pdf` (Jan→Feb 339 865 kg carry-over) and extends through May 2025.

Confirmed by OisteBio (Paolo Ughetti) 2026-05-21: no earlier BL exist; nothing has been withheld.

## Routing chain

```
Girardot (Cundinamarca, CO)            ← plant
        │  (inbound road freight from ELT suppliers — see "Pending" below)
        ▼
Cartagena port (CO)                    ← outbound ocean origin
        │  CMA CGM sea freight
        ▼
Rotterdam (NL)                         ← discharge port
        │  short-haul road
        ▼
UTB BV — Dordrecht (NL)                ← consignee / NL distribution hub
        │  20 trips, road freight (NL → UK)
        ▼
Crown Oil Limited (UK)                 ← off-taker of record (ROS submitter)
```

## Pending — inbound transport documentation

Inbound transport from ISCC-certified ELT suppliers to the Girardot plant (delivery notes, weighbridge tickets, supplier-side dispatch records) is **pending
upload by the operator**. It is documented here as a known handover item, not a blocker for the current 8-month bundle:

- The supplier-side weight figures are already reconciled in `daily_inputs` (database) and the per-month `02_mass_balance_<month>_2025_FINAL.pdf` reports — those derive from the certified-source xlsx logs the suppliers send with each delivery.
- The physical transport receipts (CMR / waybills) are held by the suppliers and the Girardot gate-house in paper form. Digital scans will be added to this folder as they are uploaded.

If the ISCC EU auditor requests them for a specific delivery, OisteBio retrieves them on demand from the gate-house archive.

## Audit checklist

- [x] Outbound ocean leg (CO → NL): 2 BL covering shipments June + July 2025.
- [x] NL → UK road leg: arrivals tracker with PoS refs OISCRO-0013-25 .. 0032-25.
- [x] Pre-export stockpile gap (Jan–May 2025): confirmed by operator, no BL pre-June.
- [ ] Inbound supplier → plant transport: paper-only, scans pending upload.
