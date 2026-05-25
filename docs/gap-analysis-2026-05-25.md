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

| # | Gap | Evidenza | Impatto audit | Plane |
|---|---|---|---|---|
| **G1** | Step 3 transload report UTB-2025-Q3-CONSOLIDATED — no PDF | `shipment_leg id=3 pdf_ref NULL` | ISCC §5 continuità massa UTB | DFTEN-166 |
| **G2** | Step 4 delivery_uk JLY001-JLY020 — no PDF aggregato | `shipment_leg id=4 pdf_ref NULL` (20 invoice singoli esistono su disk) | RTFO closing-leg evidence | DFTEN-167 |
| **G3** | UTB BV ISCC cert — su Drive non in DB | Drive `CERTIFICATE UTB BV.pdf` esistente; `operator_certificate_id` su shipment_leg NULL | `shipment_leg.operator_certificate_id` FK richiesto | DFTEN-168 |
| **G4** | GHG CI per-batch non tracciato | No `ghg_calculations` table; `consignment_pos.ghg_*` columns esistono ma NULL su prod | rtfo-gap §3.2 — Annex D counterfactual mandatory per RCF | DFTEN-128, 129 (E3) |
| **G5** | Feedstock classification (`rtfo_class`) | No `feedstocks` table | rtfo-gap §3.1 — RTFO List of Feedstocks obbligatorio | DFTEN-124, 125, 126, 127 (E3) |
| **G6** | PoS file archiving | `consignment_pos.pdf_ref` schema c'è ma da popolare | rtfo-coc:32 PoS storage | DFTEN-169 |
| **G7** | PDF signing + SHA-256 hash | Nessun signer implementato | mass-balance §6 CEO signature + hash | DFTEN-170 |
| **G8** | Audit log CSV export | endpoint solo JSON | blueprint-activities:62 RFC4180+BOM | DFTEN-103 (reopened) |
| **G9** | RTFO-310825 bundle automation | Manual artifacts esistono (memoria), no generator | blueprint-activities:392 multi-page ZIP | DFTEN-151 (urgent) |
| **G10** | ROS export schema | Phase 3 backlog | rtfo-gap:111-118 | DFTEN-146, 147, 152 (E5) |

---

## 3. Gap code-quality

Non bloccano audit, bloccano DX e generano bug latenti.

| # | Problema | File | Effetto | Plane |
|---|---|---|---|---|
| **C1** | `consignment_pos` ORM PK composito vs DB surrogate | `app/models/consignment_pos.py:23-28` vs 0028:49-52 | ORM INSERT romperà | DFTEN-171 |
| **C2** | `consignment_pos.issuance_date` mancante ORM | 0027:38 vs model.py | `warehouse.py:94` raw SQL workaround | DFTEN-172 |
| **C3** | `inland_shipment` no ORM model | 0023 + `ersv_renderer.py:1114-1130` raw SQL | No schema validation Pydantic | DFTEN-173 |
| **C4** | `mass_balance_ledger` no ORM model | 0024 + backfill scripts raw SQL | Stesso problema | DFTEN-174 |
| **C5** | `byproduct_buyer` + `byproduct_sale` no ORM | 0026 + `byproduct_sales.py` raw SQL | Stesso | DFTEN-175 |
| **C6** | `shipment_unit` no `updated_at` né `deleted_at` | `app/models/shipment_unit.py:33` | Inconsistente con pattern soft-delete progetto | quick-win |
| **C7** | eRSV outbound allocation non-idempotent | `ersv_renderer.py` race condition | UNIQUE violation sotto carico | (TBD) |
| **C8** | Byproduct sale → ledger non-transazionale | `byproduct_sales.py:270-340` | Orphaned sale row se ledger fallisce | DFTEN-176 |
| **C9** | PDF stream paths solo runtime validation | `consignments.py:479-480, 543-544` | DB accetta TEXT arbitrario | quick-win |

---

## 4. Gap frontend (UI completeness)

| # | Area | Stato | Mancante | Plane |
|---|---|---|---|---|
| **F1** | logistics/[id] Ocean BL chip | ✅ wired (e2629fc) | — | done |
| **F2** | logistics/[id] EAD/Invoice/eRSV-out chip | ✅ wired | Edge case: `invoice_pdf_ref` esiste ma `invoice_no` null → no chip | DFTEN-177 |
| **F3** | logistics/[id] Step 3 transload | ⚠️ no chip | Dipende G1 | DFTEN-166 (cover) |
| **F4** | logistics/[id] Step 4 delivery_uk | ⚠️ no chip | Dipende G2 | DFTEN-167 (cover) |
| **F5** | certificates/[id] detail | ⚠️ external ISCC Hub only | No internal PDF viewer (operator_certificate.pdf_ref column manca) | DFTEN-178 |
| **F6** | contracts/[id] detail | ⚠️ no PDF viewer | Files su disk `backend/data/contracts/` (16M, 7 file) ma no link | DFTEN-179 |
| **F7** | suppliers/[id] detail | ⚠️ niente eRSV inbound list | drill-down assente | DFTEN-180 |
| **F8** | warehouse/movements `ref_doc_no` | ⚠️ static text | non clickable, dovrebbe aprire modal per doc type | DFTEN-181 |
| **F9** | reports/closure-status drill-down | ⚠️ no daily input link | investigazione anomaly impossibile da UI | DFTEN-182 |
| **F10** | UTB ISCC cert popup | ⚠️ — | Dipende G3 | DFTEN-168 (cover) |

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

### FASE 1 — Audit handover bloccanti (2-3 giorni) · Plane Module **E8**

**Target:** chiudere documenti mancanti per consignment c-1 + UTB cert.

**Plane issues coperte:** DFTEN-166, 167, 168, 169, 177, 151.

1. **G3 — UTB BV ISCC cert** · DFTEN-168
   - Download da Drive: `gdrive:DFT_2025/RTFO-310825/03_supplier_evidence/certificates/CERTIFICATE UTB BV.pdf`
   - Storage: `backend/data/certificates/utb-bv/`
   - Migration `0033_operator_certificate_pdf_ref.py`: `ALTER TABLE operator_certificate ADD pdf_ref TEXT`
   - Backfill: INSERT operator_certificate UTB BV + UPDATE `shipment_leg.operator_certificate_id` su leg #3
   - Route stream: `/operator-certificates/{id}.pdf`
   - Frontend: chip "ISCC" sotto leg #3 (riusa pattern `OceanBlLink`)

2. **G1 — Transload report UTB Q3** · DFTEN-166
   - Serve file utente: `UTB-2025-Q3-CONSOLIDATED.pdf` (non su Drive)
   - Storage: `backend/data/transload/c-1/`
   - Schema: `shipment_leg.pdf_ref` già esiste — solo backfill row #3
   - Frontend: chip "PDF" su leg #3

3. **G2 — Bundle invoice JLY001-JLY020** · DFTEN-167
   - Opzione A: utente fornisce bundle aggregato
   - Opzione B: server-side concat dei 20 PDF in `JLY001-020-bundle.pdf` con `pypdf`
   - Storage: `backend/data/delivery_uk/c-1/`
   - Backfill `shipment_leg #4.pdf_ref` + chip

4. **G6 — Backfill PoS pdf_ref** · DFTEN-169
   - Script `scripts/backfill_pos_pdf_ref.py` — match `pos_number` ↔ file su `data/pos_documents/c-1/`
   - Frontend: drilldown chip su PoS list

5. **F2 — Edge case invoice chip** · DFTEN-177
   - Fix `ChainTimeline.tsx:99` — `leg.invoice_pdf_ref && !leg.invoice_no` → fallback ref

**Deliverable:** chain-of-custody c-1 mostra 6/6 documenti chip cliccabili.

---

### FASE 2 — ORM drift (3 giorni) · Plane Module **E9**

**Target:** fix code-quality blockers prima di nuovi feature.

**Plane issues coperte:** DFTEN-171, 172, 173, 174, 175, 176.

6. **C1 — consignment_pos PK surrogate** · DFTEN-171

   ```python
   # app/models/consignment_pos.py
   id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
   consignment_id: Mapped[int] = mapped_column(ForeignKey(...))
   pos_number: Mapped[str] = mapped_column(String(64))
   __table_args__ = (UniqueConstraint('consignment_id', 'pos_number'),)
   ```

7. **C2 — issuance_date in ORM** · DFTEN-172
   - Add `issuance_date: Mapped[date | None]`
   - Remove raw SQL workaround `warehouse.py:94`

8. **C3-C5 — ORM models mancanti** · DFTEN-173, 174, 175
   - `app/models/inland_shipment.py`
   - `app/models/mass_balance_ledger.py`
   - `app/models/byproduct_buyer.py` + `byproduct_sale.py`

9. **C8 — transactional byproduct sale + ledger** · DFTEN-176
   - Wrap insert in `async with session.begin():`
   - `byproduct_sales.py:270-340`

**Deliverable:** pytest passa `tests/integration/test_orm_inserts.py` (nuovo).

---

### FASE 3 — Audit-grade reporting (5-7 giorni) · Plane Module **E10**

**Plane issues coperte:** DFTEN-170, 103, 151.

10. **G7 — PDF signing + SHA-256** · DFTEN-170
    - Lib: `pyhanko` per PAdES-B sig oppure GPG detached
    - Endpoint `/sign/pdf` (admin only)
    - Hash in `audit_log.meta.sha256`

11. **G8 — Audit log CSV export** · DFTEN-103 (reopened)
    - `/audit-log/export.csv?from=...&to=...&table=...`
    - RFC4180 + BOM (Windows Excel compat)

12. **G9 — RTFO bundle generator** · DFTEN-151 (urgent)
    - Service `app/services/rtfo_bundle.py`
    - Input: consignment_id + date range
    - Output: ZIP con `manifest.json` (sha256 per file) + N PDF
    - Template basato su `RTFO-310825` esistente (50 artefatti memoria)

**Deliverable:** `/consignments/{id}/rtfo-bundle.zip` scaricabile.

---

### FASE 4 — Sustainability tracking (5 giorni) · Plane Module **E3**

**Plane issues coperte:** DFTEN-124, 125, 126, 127, 128, 129, 130, 131, 132.

13. **G5 — feedstocks table** · DFTEN-124, 125, 126, 127

    ```python
    class Feedstock(Base):
        code: str  # ELT, UCO, ...
        rtfo_class: Enum  # 'wastes-residues' | 'crops' | ...
        iscc_eu_class: str
        ghg_default_ep: Decimal | None
    ```

    - Migration `0034_feedstocks.py`
    - FK `daily_inputs.feedstock_id`

14. **G4 — ghg_calculations table** · DFTEN-128, 129

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

15. **Frontend GHG card** · DFTEN-131, 132
    - In `chain-of-custody/[id]` — chip "GHG -85%" verde se saving > 65%

**Deliverable:** RCF compliance evidence in bundle.

---

### FASE 5 — Frontend completeness (3 giorni) · Plane Module **E11**

**Plane issues coperte:** DFTEN-178, 179, 180, 181, 182.

16. **F5 — certificate detail interno** · DFTEN-178
    - Add `certificates.pdf_ref` column (migration `0035`)
    - Route `/certificates/{id}.pdf`
    - Frontend `certificates/[id]/page.tsx` viewer modal

17. **F6 — contract detail PDF** · DFTEN-179
    - 7 file in `backend/data/contracts/` da linkare

18. **F7 — supplier detail eRSV inbound list** · DFTEN-180
    - Drill-down `/suppliers/[id]` mostra eRSV inbound + cert list

19. **F8 — warehouse ref_doc_no clickable** · DFTEN-181
    - Mapping `doc_type → modal` (eRSV, PoS, BL, ...)

20. **F9 — reports drill-down** · DFTEN-182
    - Click closure-status row → modal daily_inputs origin

**Deliverable:** copertura UI 100% su tutti i documenti DB-tracked.

---

### FASE 6 — Regulatory (backlog) · Plane Modules **E5 + E1**

**Plane issues coperte:** DFTEN-146, 147, 148, 149, 150, 152, 153, 154 (E5); DFTEN-108, 109, 111, 112 (E1 close-out audit).

21. **G10 — ROS export schema** · DFTEN-146, 147, 152
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

## 8. Sequenza esecuzione (module-ordered)

```
SPRINT 1  E8  FASE 1  #1-5     audit handover bloccanti       (DFTEN-166,167,168,169,177)
SPRINT 2  E7  done    -        downstream OisteBio→Crown Oil  (DFTEN-165, retroactive marker)
SPRINT 3  E10 FASE 3  #10-12   audit-grade reporting + bundle (DFTEN-170,103,151)
SPRINT 4  E9  FASE 2  #6-9     ORM drift                      (DFTEN-171..176)
SPRINT 5  E3  FASE 4  #13-15   sustainability (feedstock+GHG) (DFTEN-124..132)
SPRINT 6  E11 FASE 5  #16-20   frontend completeness          (DFTEN-178..182)
BACKLOG   E4  -                rtfc batches + state machine   (DFTEN-133..145)
BACKLOG   E5  FASE 6  #21      ROS export + reminders         (DFTEN-146..154)
BACKLOG   E6  -                Annex D worksheet              (DFTEN-155..162)
BACKLOG   E1  -                audit close-out + ROS submit   (DFTEN-108..112)
```

**Critical path Crown Oil handover:** SPRINT 1 (E8) + SPRINT 3 #12 (E10 bundle) ≈ 5-7 giorni dev focus.

**Discipline:** ogni sprint preceduto da pre-flight ingredients analysis (vedi §11). Sprint parte solo se shopping list vuota.

---

## 10. Plane tracking (workspace `xbitagency`, project `DFTEN`)

Audit Plane 2026-05-25 — pre-fix: 119 issues, **zero** module/cycle/label structure, drift doc↔Plane su 3 ticket.

**Mutazioni eseguite:**

| Issue | Azione | Motivo |
|---|---|---|
| DFTEN-103 | Done → Todo, priority `high` + audit comment | Endpoint `/audit-log?format=csv` mancante: `grep -rn "format=csv" backend/app/` → zero match. G8 audit-blocking. |
| DFTEN-123 | Todo → Done | Sprint 3 chiuso (commit `bc893a5` + landing deploy `oistebio.usenexos.com`). |
| DFTEN-133 | Backlog → Done | `off_taker` table esiste + Crown Oil seed presente prod (1 row). |
| DFTEN-165 | CREATED (Done, retroactive) | Sprint downstream OisteBio→Crown Oil (migrations 0021-0032) — zero Plane tracking originale. |
| DFTEN-166..182 | CREATED (17 new issues) | Mapping diretto G1-G10 + C1-C5,C8 + F2,F5-F9 → Plane. |
| DFTEN-124..129 | priority bump → `high` | E3 sustainability tracking, audit-blocking lato Annex D. |
| DFTEN-151 | priority bump → `urgent` | G9 RTFO bundle generator, critical path Crown Oil handover. |

**Module structure (10 modules, no dates per requisito utente):**

| Module | Issues | Sprint |
|---|---|---|
| **E1** Audit Close-out & ROS Submit | DFTEN-108, 109, 111, 112 | backlog |
| **E2** Sprint 3 Frontend dashboard | DFTEN-123, 164 (residual) | done |
| **E3** Sustainability tracking (feedstock + GHG) | DFTEN-124..132 (9 issues) | sprint 5 |
| **E4** RTFC batches + state machine | DFTEN-133..145 (13 issues) | backlog |
| **E5** ROS export + reminders | DFTEN-146..154 (9 issues) | backlog |
| **E6** Annex D worksheet | DFTEN-155..162 (8 issues) | backlog |
| **E7** Downstream OisteBio→Crown Oil | DFTEN-165 | done (retroactive) |
| **E8** Audit handover bloccanti (G1-G3, G6, F2) | DFTEN-166, 167, 168, 169, 177, 151 | **sprint 1 — next** |
| **E9** ORM drift (C1-C5, C8) | DFTEN-171, 172, 173, 174, 175, 176 | sprint 4 |
| **E10** Audit-grade reporting (G7-G9) | DFTEN-170, 103, 151 | sprint 3 |
| **E11** Frontend completeness (F5-F9) | DFTEN-178, 179, 180, 181, 182 | sprint 6 |

**Post-fix state:** 119 issues totali, zero orfani (tutte assegnate a module). Date cycle non usate (utente: "non mi frega nulla di date"). Caveat: Plane module GET ritorna `completed_issues`/`backlog_issues` counters cached/async — usare `total_issues` field per conteggio affidabile.

**Coherence check gap-doc ↔ Plane:** 1:1 mapping verificato, zero contraddizioni. G1→166, G2→167, G3→168, G4→128+129, G5→124-127, G6→169, G7→170, G8→103, G9→151, G10→146+147+152. C1→171, C2→172, C3→173, C4→174, C5→175, C6→quick-win, C7→TBD, C8→176, C9→quick-win. F2→177, F3→166cov, F4→167cov, F5→178, F6→179, F7→180, F8→181, F9→182, F10→168cov.

---

## 11. Sprint workflow methodology

Disciplina concordata 2026-05-25: pending issues raggruppate in sprint per Plane module (§10). **Ogni sprint preceduto da pre-flight ingredients analysis. Se shopping list non vuota → spesa prima, sprint dopo.**

### Pre-flight ingredients checklist

Prima di aprire qualsiasi sprint, analizza in read-only:

1. **Schema** — migration n. richiesta esiste? FK target tables presenti? `grep -rn` migration prefix.
2. **Data** — dati operativi serviti dal sprint esistono su prod? (es. E8 richiede file PDF da utente o da Drive).
3. **External deps** — Drive remote configured? gdrive token valid? Backend container up?
4. **Code skeletons** — router/model/service paths esistono? Conflitti con codice corrente?
5. **Frontend hooks** — component pattern riusabile esiste? (es. OceanBlLink wired → riuso F10).
6. **Auth/perm** — JWT role check necessario? Migrations 0007+ già coprono ruolo?
7. **Storage path** — bind-mount Docker già definito? Quota disk sufficiente?
8. **Plane sync** — DFTEN-xxx esistono per ogni step? Priority allineata con sprint goal?

### Shopping list pattern

Output pre-flight = uno di:

- **Tutti gli ingredienti presenti** → sprint parte, esecuzione lineare
- **Shopping list non vuota** → micro-tasks (provisioning file, migration prep, auth scaffold) **prima** del sprint vero, poi sprint
- **Blocker esterno** (utente fornisce file, decisione regulatory, accesso terzo) → sprint sospeso fino al ritorno

### Pre-sprint regression guard (CRITICAL)

Aggiunto 2026-05-25 su input utente: *"non sovrascriviamo cose già fate importanti, punto cruciale e delicato"*. Progetto ha 32 migrations + 119 Plane issues + 50+ artefatti RTFO prod-deployed — single silent overwrite può rompere audit trail Crown Oil.

**Discipline rigida prima di ogni Edit/Write nello sprint:**

1. **Read THEN edit** — mai overwrite cieco. `Read` tool sul file target PRIMA di `Edit`. Inspect imports, decorator, soft-delete patterns già presenti.
2. **grep overlap** — per ogni nuovo symbol/route/table/migration: `grep -rn '<name>' backend/ landing/` per scoprire usi pre-esistenti. Tabelle: `grep -rn 'CREATE TABLE <name>' backend/alembic/versions/`.
3. **Migration check** — `ls backend/alembic/versions/` PRIMA di nuovo file. Ultima versione tracked = `0032`. Nuova migration parte da `0033_`. Mai duplicare prefix.
4. **Git clean check** — `git status --short` deve essere coerente con stato sprint. File `M` non legati allo sprint → branch separato o stash.
5. **File inventory marker** — apertura sprint produce lista file con tag `[NEW] / [EXTEND] / [REPLACE]`. `[REPLACE]` richiede conferma utente esplicita prima di toccare.
6. **Soft-deprecate, never delete** — codice obsoleto si marca `# DEPRECATED <date> — see <new>` o `@deprecated`; non si rimuove. Stessa filosofia di `deleted_at = NOW()` per DB.
7. **Existing-flow smoke test** — prima close-out sprint: pytest existing suite + manual click chain-of-custody c-1 + logistics/c-1 (già wired, baseline). Se rompe → rollback prima merge.
8. **Plane close-out comment** — su ogni DFTEN-xxx chiuso, lista file:line modificati nel comment. Audit trail completo.
9. **ASK on ambiguous overlap** — qualsiasi func/route/model che TOUCH file con >50 righe esistenti senza pattern chiaro → `AskUserQuestion` PRIMA di Edit.

**Doc storici sono pre-Sprint downstream — fonte di verità per "esistente vs missing" è il CODE (migrations 0021-0032 + ORM + router), non i doc gap-storici.** Vedi §1 doc-claim vs code-truth.

### Sprint closeout

Al termine sprint:

- PATCH Plane issues coperte → `Done`
- Update gap-doc §10 mutazioni eseguite + §8 sequenza (mark sprint completato)
- Cross-link commit hash nel sprint summary
- Run regression smoke (chain-of-custody c-1 + pytest)
- Update changelog §13 footer

---

## 12. Riferimenti file analizzati

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

---

## 13. Changelog

- **2026-05-25** — initial drop (commit `0afebdd`): §1-§9 doc-claim/code-truth, gap tables G/C/F, piano azione FASE 1-6, sequence, references.
- **2026-05-25** — Plane sync integration: added Plane column to §2/§3/§4 tables (DFTEN-xxx refs), inserted §10 Plane tracking (10 modules + mutazioni: 3 PATCH, 18 CREATE, 7 priority bump) e §11 Sprint workflow methodology (pre-flight ingredients + shopping list), §8 sequenza riscritta in chiave module-ordered. Coherence check 1:1 gap-doc ↔ Plane = zero contraddizioni.
- **2026-05-25** — Pre-sprint regression guard aggiunto a §11 (input utente: punto cruciale e delicato). 9-step discipline: Read-before-Edit, grep overlap, migration check, file inventory `[NEW]/[EXTEND]/[REPLACE]`, soft-deprecate never delete, existing-flow smoke test, Plane close-out comment, ASK on ambiguous overlap. Source-of-truth = code, NOT doc storici.
