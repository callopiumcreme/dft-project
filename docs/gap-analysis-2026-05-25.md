# Audit Gap Analysis & Action Plan — 2026-05-25

**Scope:** chain-of-custody OisteBio → Crown Oil UK (RTFO + ISCC EU), consignment c-1 (DEL-CRW-2025-1 delivered) e c-2 (DEL-CRW-2025-2 at_utb).

**Method:** 4 sweep paralleli read-only (docs + backend ORM/routers + frontend components + prod DB inventory). Tutto file:line citato. Doc-claim vs code-truth riconciliato — molti "MISSING" nei doc storici sono **DONE** in migrations 0021-0032.

**Annex of:** `docs/rtfo-gap-analysis.md` (storico, pre-Sprint downstream), `docs/stato-e-gap-catena.md`, `docs/proposta-modello-logistica-downstream.md`, `docs/mass-balance-allocation-policy.md`.

---

## 1. Doc-claim vs code-truth (riconciliazione)

I documenti gap storici sono pre-Sprint downstream. Migrations 0021-0032 hanno chiuso la maggioranza degli schema gap. Verità attuale:

| Item per doc storico | Doc dice | Code reale | Verità |
|---|---|---|---|
| Consignment model | MISSING (proposta:12) | `consignment` table 0021, ORM `app/models/consignment.py` | ✅ DONE |
| shipment_leg + units | MISSING (proposta:90-96) | 0021 + ORM + routers `/shipments/legs/*` | ✅ DONE |
| Outbound eRSV per-PoS | MISSING (mass-balance:140) | 0022 `consignment_pos.ersv_outbound_no`, renderer + endpoint `/ersv/outbound/*` | ✅ DONE |
| Inland eRSV Girardot→Cartagena | MISSING (proposta:15) | 0023 `inland_shipment.ersv_inland_no`, render endpoint | ✅ DONE (ORM gap, vedi §3) |
| UTB transload + stock residual | CRITICAL GAP (stato-e-gap:G4) | `shipment_leg.kg_stock_residual` 0021 | ✅ DONE schema, ⚠️ niente pdf transload report |
| MRN/EAD customs | MISSING (stato-e-gap:G5) | 0030 `consignment_pos_customs`, route `/consignments/{id}/customs/{mrn}.pdf` | ✅ DONE |
| Commercial invoice | MISSING (rtfo-coc:112) | 0031 `invoice_pdf_ref`, route `/invoices/{n}.pdf` | ✅ DONE |
| Ocean BL pdf | n/a | 0032 `shipment_leg.pdf_ref`, route + popup (commit e2629fc) | ✅ DONE (2026-05-25) |
| Mass-balance ledger | DOCUMENTED POLICY | 0024 `mass_balance_ledger`, backfill | ✅ DONE schema, ⚠️ no ORM |
| Audit log | IMPLEMENTED | 0001, 249 righe prod | ✅ DONE |

**Conclusione:** i doc storici vanno archiviati come `docs/_archive/*-2026-04.md`.

---

## 2. Gap reali audit-blocking

Devono chiudere prima del Crown Oil handover.

| # | Gap | Evidenza | Impatto audit |
|---|---|---|---|
| **G1** | Step 3 transload report UTB-2025-Q3-CONSOLIDATED — no PDF | `shipment_leg id=3 pdf_ref NULL` | ISCC §5 continuità massa UTB |
| **G2** | Step 4 delivery_uk JLY001-JLY020 — no PDF aggregato | `shipment_leg id=4 pdf_ref NULL` (20 invoice singoli esistono su disk) | RTFO closing-leg evidence |
| **G3** | UTB BV ISCC cert — su Drive non in DB | Drive `CERTIFICATE UTB BV.pdf` esistente; `operator_certificate_id` su shipment_leg NULL | `shipment_leg.operator_certificate_id` FK richiesto |
| **G4** | GHG CI per-batch non tracciato | No `ghg_calculations` table; `consignment_pos.ghg_*` columns esistono ma NULL su prod | rtfo-gap §3.2 — Annex D counterfactual mandatory per RCF |
| **G5** | Feedstock classification (`rtfo_class`) | No `feedstocks` table | rtfo-gap §3.1 — RTFO List of Feedstocks obbligatorio |
| **G6** | PoS file archiving | `consignment_pos.pdf_ref` schema c'è ma da popolare | rtfo-coc:32 PoS storage |
| **G7** | PDF signing + SHA-256 hash | Nessun signer implementato | mass-balance §6 CEO signature + hash |
| **G8** | Audit log CSV export | endpoint solo JSON | blueprint-activities:62 RFC4180+BOM |
| **G9** | RTFO-310825 bundle automation | Manual artifacts esistono (memoria), no generator | blueprint-activities:392 multi-page ZIP |
| **G10** | ROS export schema | Phase 3 backlog | rtfo-gap:111-118 |

---

## 3. Gap code-quality

Non bloccano audit, bloccano DX e generano bug latenti.

| # | Problema | File | Effetto |
|---|---|---|---|
| **C1** | `consignment_pos` ORM PK composito vs DB surrogate | `app/models/consignment_pos.py:23-28` vs 0028:49-52 | ORM INSERT romperà |
| **C2** | `consignment_pos.issuance_date` mancante ORM | 0027:38 vs model.py | `warehouse.py:94` raw SQL workaround |
| **C3** | `inland_shipment` no ORM model | 0023 + `ersv_renderer.py:1114-1130` raw SQL | No schema validation Pydantic |
| **C4** | `mass_balance_ledger` no ORM model | 0024 + backfill scripts raw SQL | Stesso problema |
| **C5** | `byproduct_buyer` + `byproduct_sale` no ORM | 0026 + `byproduct_sales.py` raw SQL | Stesso |
| **C6** | `shipment_unit` no `updated_at` né `deleted_at` | `app/models/shipment_unit.py:33` | Inconsistente con pattern soft-delete progetto |
| **C7** | eRSV outbound allocation non-idempotent | `ersv_renderer.py` race condition | UNIQUE violation sotto carico |
| **C8** | Byproduct sale → ledger non-transazionale | `byproduct_sales.py:270-340` | Orphaned sale row se ledger fallisce |
| **C9** | PDF stream paths solo runtime validation | `consignments.py:479-480, 543-544` | DB accetta TEXT arbitrario |

---

## 4. Gap frontend (UI completeness)

| # | Area | Stato | Mancante |
|---|---|---|---|
| **F1** | logistics/[id] Ocean BL chip | ✅ wired (e2629fc) | — |
| **F2** | logistics/[id] EAD/Invoice/eRSV-out chip | ✅ wired | Edge case: `invoice_pdf_ref` esiste ma `invoice_no` null → no chip |
| **F3** | logistics/[id] Step 3 transload | ⚠️ no chip | Dipende G1 |
| **F4** | logistics/[id] Step 4 delivery_uk | ⚠️ no chip | Dipende G2 |
| **F5** | certificates/[id] detail | ⚠️ external ISCC Hub only | No internal PDF viewer (operator_certificate.pdf_ref column manca) |
| **F6** | contracts/[id] detail | ⚠️ no PDF viewer | Files su disk `backend/data/contracts/` (16M, 7 file) ma no link |
| **F7** | suppliers/[id] detail | ⚠️ niente eRSV inbound list | drill-down assente |
| **F8** | warehouse/movements `ref_doc_no` | ⚠️ static text | non clickable, dovrebbe aprire modal per doc type |
| **F9** | reports/closure-status drill-down | ⚠️ no daily input link | investigazione anomaly impossibile da UI |
| **F10** | UTB ISCC cert popup | ⚠️ — | Dipende G3 |

---

## 5. Prod data state (oistebio, snapshot 2026-05-25)

```
consignment           : 2 (DEL-CRW-2025-1 delivered_uk, DEL-CRW-2025-2 at_utb)
shipment_leg          : 4 (2 con pdf_ref → BL ocean, 2 senza)
consignment_pos       : 32
consignment_pos_customs: 20
inland_shipment       : 29
shipment_unit         : 29
mass_balance_ledger   : 3112 entries
audit_log             : 249 rows, 10 tables
certificates          : 18
suppliers             : 13
off_taker             : 1 (Crown Oil)
```

**Anomalie data state:**

- `consignment.ersv_outbound_no` + `port_rsv_no` ENTRAMBI NULL → coerente: per-PoS `consignment_pos.ersv_outbound_no` è canale corretto post-refactor (commit `14868f5`). Colonne consignment-level vanno deprecate o backfilled dalla view `v_chain_summary`.
- 20 file in `/data/customs/c-1/` + 20 in `/data/invoices/c-1/` coerenti con `consignment_pos_customs` (20 righe).
- ORM PK drift `consignment_pos` post-0028: surrogate `id BIGSERIAL` su prod ma ORM ha PK composito → C1 da fixare prima di nuovi feature consignment_pos.

---

## 6. Piano di azione

### FASE 1 — Audit handover bloccanti (2-3 giorni)

**Target:** chiudere documenti mancanti per consignment c-1 + UTB cert.

1. **G3 — UTB BV ISCC cert**
   - Download da Drive: `gdrive:DFT_2025/RTFO-310825/03_supplier_evidence/certificates/CERTIFICATE UTB BV.pdf`
   - Storage: `backend/data/certificates/utb-bv/`
   - Migration `0033_operator_certificate_pdf_ref.py`: `ALTER TABLE operator_certificate ADD pdf_ref TEXT`
   - Backfill: INSERT operator_certificate UTB BV + UPDATE `shipment_leg.operator_certificate_id` su leg #3
   - Route stream: `/operator-certificates/{id}.pdf`
   - Frontend: chip "ISCC" sotto leg #3 (riusa pattern `OceanBlLink`)

2. **G1 — Transload report UTB Q3**
   - Serve file utente: `UTB-2025-Q3-CONSOLIDATED.pdf` (non su Drive)
   - Storage: `backend/data/transload/c-1/`
   - Schema: `shipment_leg.pdf_ref` già esiste — solo backfill row #3
   - Frontend: chip "PDF" su leg #3

3. **G2 — Bundle invoice JLY001-JLY020**
   - Opzione A: utente fornisce bundle aggregato
   - Opzione B: server-side concat dei 20 PDF in `JLY001-020-bundle.pdf` con `pypdf`
   - Storage: `backend/data/delivery_uk/c-1/`
   - Backfill `shipment_leg #4.pdf_ref` + chip

4. **G6 — Backfill PoS pdf_ref**
   - Script `scripts/backfill_pos_pdf_ref.py` — match `pos_number` ↔ file su `data/pos_documents/c-1/`
   - Frontend: drilldown chip su PoS list

5. **F2 — Edge case invoice chip**
   - Fix `ChainTimeline.tsx:99` — `leg.invoice_pdf_ref && !leg.invoice_no` → fallback ref

**Deliverable:** chain-of-custody c-1 mostra 6/6 documenti chip cliccabili.

---

### FASE 2 — ORM drift (3 giorni)

**Target:** fix code-quality blockers prima di nuovi feature.

6. **C1 — consignment_pos PK surrogate**

   ```python
   # app/models/consignment_pos.py
   id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
   consignment_id: Mapped[int] = mapped_column(ForeignKey(...))
   pos_number: Mapped[str] = mapped_column(String(64))
   __table_args__ = (UniqueConstraint('consignment_id', 'pos_number'),)
   ```

7. **C2 — issuance_date in ORM**
   - Add `issuance_date: Mapped[date | None]`
   - Remove raw SQL workaround `warehouse.py:94`

8. **C3-C5 — ORM models mancanti**
   - `app/models/inland_shipment.py`
   - `app/models/mass_balance_ledger.py`
   - `app/models/byproduct_buyer.py` + `byproduct_sale.py`

9. **C8 — transactional byproduct sale + ledger**
   - Wrap insert in `async with session.begin():`
   - `byproduct_sales.py:270-340`

**Deliverable:** pytest passa `tests/integration/test_orm_inserts.py` (nuovo).

---

### FASE 3 — Audit-grade reporting (5-7 giorni)

10. **G7 — PDF signing + SHA-256**
    - Lib: `pyhanko` per PAdES-B sig oppure GPG detached
    - Endpoint `/sign/pdf` (admin only)
    - Hash in `audit_log.meta.sha256`

11. **G8 — Audit log CSV export**
    - `/audit-log/export.csv?from=...&to=...&table=...`
    - RFC4180 + BOM (Windows Excel compat)

12. **G9 — RTFO bundle generator**
    - Service `app/services/rtfo_bundle.py`
    - Input: consignment_id + date range
    - Output: ZIP con `manifest.json` (sha256 per file) + N PDF
    - Template basato su `RTFO-310825` esistente (50 artefatti memoria)

**Deliverable:** `/consignments/{id}/rtfo-bundle.zip` scaricabile.

---

### FASE 4 — Sustainability tracking (5 giorni)

13. **G5 — feedstocks table**

    ```python
    class Feedstock(Base):
        code: str  # ELT, UCO, ...
        rtfo_class: Enum  # 'wastes-residues' | 'crops' | ...
        iscc_eu_class: str
        ghg_default_ep: Decimal | None
    ```

    - Migration `0034_feedstocks.py`
    - FK `daily_inputs.feedstock_id`

14. **G4 — ghg_calculations table**

    ```python
    class GhgCalculation(Base):
        consignment_pos_id: int  # FK
        ep: Decimal       # production emissions
        etd: Decimal      # transport
        eccs: Decimal     # CCS credit
        total: Decimal    # GENERATED
        saving_pct: Decimal  # vs fossil counterfactual 94 gCO2/MJ
        methodology: str  # 'annex-d-rcf' | 'annex-v'
    ```

    - Annex D counterfactual (94 gCO2/MJ fossil baseline)
    - Per-batch link a `consignment_pos`

15. **Frontend GHG card**
    - In `chain-of-custody/[id]` — chip "GHG -85%" verde se saving > 65%

**Deliverable:** RCF compliance evidence in bundle.

---

### FASE 5 — Frontend completeness (3 giorni)

16. **F5 — certificate detail interno**
    - Add `certificates.pdf_ref` column (migration `0035`)
    - Route `/certificates/{id}.pdf`
    - Frontend `certificates/[id]/page.tsx` viewer modal

17. **F6 — contract detail PDF**
    - 7 file in `backend/data/contracts/` da linkare

18. **F7 — supplier detail eRSV inbound list**
    - Drill-down `/suppliers/[id]` mostra eRSV inbound + cert list

19. **F8 — warehouse ref_doc_no clickable**
    - Mapping `doc_type → modal` (eRSV, PoS, BL, ...)

20. **F9 — reports drill-down**
    - Click closure-status row → modal daily_inputs origin

**Deliverable:** copertura UI 100% su tutti i documenti DB-tracked.

---

### FASE 6 — Regulatory (backlog)

21. **G10 — ROS export schema**
    - Phase 3 — Crown Oil responsibility
    - Output ROS CSV format (DfT spec)

---

### Quick-wins paralleli

- **C6** — `shipment_unit` add `updated_at` + `deleted_at`
- **C9** — PDF path DB constraint `CHECK (pdf_ref ~ '^c-\d+/.*\.pdf$')`
- Docs stale: rename `docs/rtfo-gap-analysis.md` → `docs/_archive/rtfo-gap-analysis-2026-04.md`

---

## 7. Decisione tecnica residua

**Compose port drift (commit f3eaed5):**

- **Opzione A (raccomandata):** `docker-compose.yml` con prod port 8000 + `docker-compose.override.yml` gitignored con dev 18000
- **Opzione B:** marker `# NEVER-RSYNC` nel file + rsync exclude

Suggerimento: A — convenzione standard Docker, zero attrito.

---

## 8. Sequenza esecuzione consigliata

```
[OGGI/DOMANI]   FASE 1 #1-5 (audit handover)
[SETTIMANA]     FASE 2 #6-9 (ORM)
[+1 SETTIMANA]  FASE 3 #10-12 (bundle)
[+2 SETTIMANE]  FASE 4 #13-15 (GHG)
[+3 SETTIMANE]  FASE 5 #16-20 (UI completeness)
[BACKLOG]       FASE 6 #21 (ROS)
```

**Critical path Crown Oil handover:** FASE 1 + FASE 3 #12 (bundle) ≈ 5-7 giorni dev focus.

---

## 9. Riferimenti file analizzati

**Backend ORM/routers:**
- `backend/app/models/consignment_pos.py:23-28` — PK drift
- `backend/app/models/shipment_unit.py:33` — manca timestamps
- `backend/app/routers/consignments.py:479-480, 543-544` — PDF stream paths
- `backend/app/routers/warehouse.py:94` — raw SQL workaround
- `backend/app/routers/byproduct_sales.py:270-340` — non-transactional
- `backend/app/services/ersv_renderer.py:1114-1130` — raw SQL inland_shipment
- `backend/alembic/versions/0021_*` → `0032_*` — schema migrations downstream

**Frontend:**
- `landing/src/components/logistics/ChainTimeline.tsx:106-127` — OceanBlLink wiring
- `landing/src/components/bl/ocean-bl-modal.tsx` — modal pattern (riusare per UTB cert)
- `landing/src/components/chain-of-custody/ChainOfCustodySummary.tsx` — recap widget
- `landing/src/app/api/consignments/[id]/bl/[blNo]/pdf/route.ts` — auth-gated proxy template

**Storage convention:**
- Ocean BL: `data/bl_ocean/c-<id>/BL_<no>_<VESSEL>_<YYYY-MM-DD>.pdf`
- EAD: `data/customs/c-<id>/<MRN>.pdf`
- Invoice: `data/invoices/c-<id>/<no>.pdf`
- (proposto) ISCC cert: `data/certificates/<operator-slug>/<cert-id>.pdf`
- (proposto) Transload: `data/transload/c-<id>/<report-id>.pdf`

---

*Documento generato 2026-05-25 — annex a `docs/rtfo-gap-analysis.md`.*
