# Proposta modello dati — Logistica downstream (D → H)

> **Status:** LOCKED post decisioni cliente · **Data:** 2026-05-23
> **Prerequisito:** `docs/stato-e-gap-catena.md` (gap analysis)
> **Scope:** chiudere la gamba a valle (vendita EU → Cartagena → BL transoceanico → UTB BV travaso → MRN UK → consegna Bury)
> **Vincolo:** non rompere niente di esistente (A–C: `daily_inputs`/`daily_production`/`certificates` restano intatti)

---

## 0. Decisioni cliente (2026-05-23) — LOCKED

| Q | Decisione | Impatto modello |
|---|-----------|------------------|
| **Q1** | **b)** tabella ponte M:N `consignment_production_link(consignment_id, prod_date, kg_allocated)` | `daily_production` resta intatto; allocazione kg per consignment via tabella ponte |
| **Q2** | OisteBio emette suo eRSV outbound. **Formato numerazione esempio:** `CO/25/007/...` (CO=Colombia, 25=anno, 007=seq — formato esatto da confermare) | Estensione renderer eRSV con `direction = outbound`; consignment ha `ersv_outbound_no` |
| **Q3** | Tutti i 20 PoS vanno a Crown Oil. **20 file** `OutgoingMaterial_Declaration_OISCRO-0013..0032-25.pdf` esistono già in `gdrive:DFT_2025/POS TO CROWN/`. Default confermato → 1 consignment + N PoS via tabella `consignment_pos` | Tabella `consignment_pos(consignment_id, pos_number, pdf_ref)` |
| **Q4** | **a)** campo `kg_stock_residual` su `utb_transload` leg | No entità separata `utb_stock` per ora |
| **Q5** | **b)** 1 `shipment_leg` per BL + tabella `shipment_unit(leg_id, container_ref, kg_net)` con granularità container | Mass-balance per BL (aggregato) + tracciamento container-level |
| **Q6** | OK nuova sezione `/app/logistics` in nav | Sidebar landing aggiunge link Logistics |
| **Q7** | Default → solo backfill audit window Jan–Aug 2025 | Migration data backfill solo per i 2 BL e 20 PoS del period |
| **Q8** | OK workflow status `consignment` | Auto-update via trigger su last leg + UI button manuale |

**Note Q2/Q3 da chiarire:**
- Format esatto `CO/25/007/...` — cliente da definire ultimo segmento (Q? settimana? mese?)
- I PoS `OISCRO-XXXX-25` sono Outgoing Material Declaration ISCC (PoS standard). L'eRSV outbound `CO/25/007/...` è documento **distinto** dal PoS? O coincide? **Da confermare**.

---

## 1. Obiettivo

Trasformare in **dati strutturati** ciò che oggi vive solo come prosa nei `transport_note.md` e nei BL PDF scansionati. Una volta fatto: ricostruzione catena di custodia end-to-end è una query, non un esercizio archeologico.

Caso d'uso reale già pronto: i dati estratti il 2026-05-23 dai 2 BL (29 container CO→NL, 20 ISO tank NL→UK, residuo UTB 75.860 kg) entrano dritti nel modello come **test di validazione**.

---

## 2. Entità proposte (3 nuove + 1 estensione)

### 2.1 `off_taker` (NEW) — buyer finale
> Crown Oil è oggi solo testo. Diventa record.

| Campo | Tipo | Note |
|-------|------|------|
| id | bigint PK | |
| code | text UQ | es. `CROWN-OIL-UK` |
| name | text | "Crown Oil Ltd" |
| country | text | "GB" |
| address | text | "Bury, UK" |
| iscc_certificate_id | bigint FK→`certificates` NULL | se buyer ha ISCC propria |
| notes | text | |
| `created_at/updated_at/deleted_at` | — | soft delete standard |

**Cardinalità:** singolo record oggi (Crown Oil UK), modello tiene N per flessibilità futura.

---

### 2.2 `consignment` (NEW) — lotto prodotto finito spedito
> Aggrega quanto prodotto a Girardot diventa "una partita commerciale".

| Campo | Tipo | Note |
|-------|------|------|
| id | bigint PK | |
| code | text UQ | es. `CONS-2025-06-CARTAGENA-EXPRES` o `CONS-OISCRO-0013-25` |
| off_taker_id | bigint FK→`off_taker` | Crown Oil |
| contract_ref | text | link a `contracts.code` se applicabile |
| product_grade | text | `DEV-P100` / `DEV-P200` |
| prod_date_from | date | finestra produzione coperta |
| prod_date_to | date | |
| total_kg | numeric(14,3) | massa totale partita (somma BL legs) |
| ersv_outbound_no | text NULL | numero eRSV OisteBio→porto (oggi non esiste, gap E2) |
| port_rsv_no | text NULL | Port RSV Cartagena |
| pos_number | text NULL | OISCRO-XXXX-25 (M:1 con consignment? vedere §5 Q3) |
| status | text | `draft` / `loaded` / `in_transit` / `at_utb` / `delivered_uk` / `closed` |
| notes | text | |
| `created_at/updated_at/deleted_at` | — | |

**Relazione con `daily_production`:** view o tabella ponte `consignment_production_link(consignment_id, prod_date, kg_allocated)` per tracciare quale produzione confluisce in quale lotto. *Decisione cliente §5 Q1.*

---

### 2.3 `shipment_leg` (NEW) — gamba logistica singola
> Una riga per ogni nodo della catena. Permette mass-balance per leg e auditabilità step-by-step.

| Campo | Tipo | Note |
|-------|------|------|
| id | bigint PK | |
| consignment_id | bigint FK→`consignment` | |
| seq | int | ordine leg (1=plant→port, 2=port→ocean, 3=ocean→NL, 4=UTB transload, 5=NL→UK, 6=UK→Bury) |
| leg_type | text | enum: `plant_to_port` / `port_loading` / `bl_ocean` / `utb_transload` / `nl_to_uk_export` / `delivery_uk` |
| document_type | text | `eRSV_outbound` / `Port_RSV` / `BL_ocean` / `transload_report` / `MRN` / `BL_road` / `commercial_invoice` |
| document_ref | text | numero documento (es. BL `CMDU856254189`) |
| document_date | date | |
| carrier | text NULL | nave/vettore (es. "CARTAGENA EXPRES voy 007CONU", "CMA CGM") |
| origin_node | text | "Girardot" / "Cartagena" / "Rotterdam" / "Dordrecht (UTB BV)" / "Bury" |
| destination_node | text | |
| container_or_tank_ref | text NULL | es. "PCVU3502178" (ISO container) o "T-12345" (ISO tank) |
| kg_in | numeric(14,3) | massa in ingresso al nodo |
| kg_out | numeric(14,3) | massa in uscita dal nodo |
| operator_certificate_id | bigint FK→`certificates` NULL | UTB BV ISCC cert qui |
| notes | text | |
| `created_at/updated_at/deleted_at` | — | |

**Vincoli:**
- Per `leg_type = utb_transload`: `kg_in = kg_out` (transloading puro, no processing) → check SQL trigger o validazione applicativa
- Per ogni leg: `kg_in >= kg_out` (no creazione massa)
- Somma `kg_out` ultimo leg (`delivery_uk`) per un consignment ≤ `consignment.total_kg`
- `seq` unico per consignment

---

### 2.4 Estensione `ersv` (EXISTING) — direzione inbound/outbound
> Oggi renderer eRSV è solo inbound (fornitore→Girardot). L'uscita verso porto richiede eRSV OisteBio→buyer.

| Cambio | Dove |
|--------|------|
| Aggiungere `direction` enum: `inbound` / `outbound` | `services/ersv_renderer.py` + template |
| Outbound usa `consignment_id` invece di `daily_input_id` | endpoint `routers/ersv.py` |
| Template HTML/PDF specifico per outbound | `templates/ersv_outbound.html` |

---

## 3. Diagramma ER (testuale)

```
   suppliers ──┐
               │ (existing M2M)
   supplier_certificates
               │
   certificates
               │ (FK NEW)
               ├──< off_taker.iscc_certificate_id
               │
               └──< shipment_leg.operator_certificate_id   (es. UTB BV cert)

   daily_production ────?───< consignment_production_link >──── consignment
                                                                    │
                                                                    │ (off_taker)
                                                                    ▼
                                                                off_taker (Crown Oil)
                                                                    │
                                                                    │ (1:N)
                                                                    ▼
   consignment ───< shipment_leg
                       (seq 1..6, leg_type, kg_in, kg_out, doc_ref)
```

---

## 4. Esempio reale — applicato ai dati 2026-05-23

**Consignment:** `DEL-CRW-2025-2`
- off_taker = Crown Oil UK
- prod_date_from = 2025-06-XX, prod_date_to = 2025-08-XX
- total_kg = 576.270 (somma 2 BL arrivo NL)
- pos_number = lista OISCRO-0013-25 .. OISCRO-0032-25 (vedi §5 Q3)
- status = `delivered_uk` (per i 20 tank già consegnati) — ma residuo 75.860 kg ancora `at_utb`

**Shipment legs (Cartagena→UK, BL1 esempio):**

| seq | leg_type | document_ref | carrier | origin → dest | kg_in | kg_out | container/tank |
|-----|----------|--------------|---------|---------------|-------|--------|-----------------|
| 1 | bl_ocean | CMDU856254189 | CARTAGENA EXPRES 007CONU | Cartagena → Rotterdam | 298.129 | 298.129 | 15× 20' ISO (PCVU3502178, ...) |
| 1 | bl_ocean | CMDU877254433 | ISTANBUL EXPRES 005COEN | Cartagena → Rotterdam | 278.141 | 278.141 | 14× 20' ISO |
| 2 | utb_transload | UTB-2025-XXX | UTB BV Dordrecht | Dordrecht → Dordrecht | 576.270 | 500.410 | (29 ISO → 20 ISO tank) |
| 3 | nl_to_uk_export | MRN-GB-XXX | road carrier | Dordrecht → Bury | 500.410 | 500.410 | 20× ISO tank |
| 4 | delivery_uk | JLY001..JLY020 | — | Bury (delivered) | 500.410 | 500.410 | — |

Residuo 75.860 kg → leg `utb_transload` ha `kg_out < kg_in` apparente, ma residuo sta in **stock UTB** non perso → da modellare come `kg_stock_residual` o split in più transload legs (uno per ogni shipment NL→UK).

→ **Decisione cliente §5 Q4.**

---

## 5. Domande aperte per il cliente

> Servono per chiudere prima di scrivere migration.

| # | Domanda | Opzioni / contesto |
|---|---------|---------------------|
| **Q1** | `consignment` ↔ `daily_production`: link diretto o via tabella ponte? | a) FK semplice `daily_production.consignment_id` (1 prod_day = 1 consignment max) <br> b) tabella M:N `consignment_production_link` con `kg_allocated` (più flessibile, gestisce split) <br> **Raccomando b)** perché produzione di un giorno può finire in due partite diverse |
| **Q2** | `eRSV outbound`: numero generato da noi o ricevuto da OisteBio Girardot? | Oggi inbound è eRSV fornitore. Outbound presumibilmente OisteBio emette → numerazione OisteBio? Servono regole numerazione + template legale |
| **Q3** | `pos_number` vs `consignment`: cardinalità? | 20 PoS Crown (OISCRO-0013..0032) per 1 consignment, o 20 consignment separati? <br> **Default proposto:** 1 consignment grande "Q3 2025", N PoS legati come array (tabella `consignment_pos`) |
| **Q4** | Modellare **stock UTB** come entità o come `kg_stock_residual` su transload leg? | a) campo `kg_stock_residual` su `utb_transload` leg <br> b) entità `utb_stock` separata con giacenza giornaliera <br> **Raccomando a)** per ora — semplice. Se UTB diventa hub multi-buyer → b) |
| **Q5** | Tracciamento container-level: 1 riga per container o aggregato per BL? | a) 1 `shipment_leg` per container (29 righe per CO→NL) <br> b) 1 leg per BL + tabella `shipment_unit(leg_id, container_ref, kg_net)` <br> **Raccomando b)** per non esplodere `shipment_leg` |
| **Q6** | UI: pagina dedicata `/app/shipments` o estensione `/app/reports`? | Suggerisco nuova sezione **Logistics** in nav, sotto Reports |
| **Q7** | Backfill storico: solo `RTFO-310825` window (Jan–Aug 2025) o tutto pregresso? | Default: solo audit window |
| **Q8** | Stato/workflow `consignment`: lo gestiamo noi o cliente vuole transizioni manuali? | Auto-update via trigger su last leg vs UI button "Mark as delivered" |

---

## 6. Out of scope (per ora)

- Integrazione real-time con CMA CGM API (BL live tracking) → manuale
- OCR automatico BL PDF scansionati → manuale, per ora carico via form admin
- Customs/MRN integration con UK gov → manuale, salviamo solo MRN come stringa

---

## 7. Sequenza implementativa proposta (post decisione cliente)

1. **Migration 0020** — `off_taker`, `consignment`, `consignment_pos`, `shipment_leg`, `shipment_unit`
2. **Seed** — Crown Oil UK come unico off_taker; UTB BV come operator_certificate
3. **Backfill** — i 2 BL già estratti come primo consignment di validazione
4. **API** — `/shipments/consignments`, `/shipments/legs`, `/shipments/units`
5. **UI** — `/app/logistics` lista consignment + dettaglio chain-of-custody
6. **eRSV outbound** — renderer + template (Sprint successivo)

---

## 8. Riepilogo in una frase

> 3 entità nuove (`off_taker`, `consignment`, `shipment_leg`) + 1 ponte container (`shipment_unit`) + estensione eRSV. Costo: 1 migration, ~5 endpoint, 1 pagina UI. Beneficio: catena ELT→Bury queryabile end-to-end, mass-balance per nodo, audit-ready.
