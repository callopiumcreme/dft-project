# Analisi xlsx Girardot 2025 — Mappatura DB

**File source:** `Girardot producciòn Enero 2025.xlsx` (Drive ID `1FWeZs6nxmM_STzFZLGFVpPCBU877Uukw`)
**Folder:** `DFT_2025/2025/` (`1jC39kiulY-6utuYsuhY2SgNqRpkQtiB5`)
**Data analisi:** 2026-05-08
**Periodo coperto:** 2025-01-02 → 2025-09-30 (222 giorni operativi, 9 sheets mensili)

---

## 1. Struttura xlsx

### Sheets
| Sheet | Entries | Suppliers presenti |
|-------|--------:|-------------------|
| JANUARY2025 | 187 | BIOWASTE, ESENTTIA, LITOPLAS |
| FEBRUARY2025 | 241 | + CIECOGRAS, SANIMAX, ≤5 TON |
| MARCH 2025 | 233 | id |
| APRIL 2025 | 300 | id |
| MAY 2025 | 267 | id |
| JUNE 2025 | 270 | id |
| JULY 2025 | 328 | id |
| AUGUST 2025 | 287 | id |
| SEPTEMBER 2025 | 316 | + ECODIESEL |
| **TOTALE** | **2429** | 7 suppliers |

### Layout per sheet (ripetuto)
```
R1-15  : header recap 2024 (OCT/NOV/DEC 2024 totals + MASS BALANCE YEAR 2024 END)
R16    : "LOADING SUMMARY - ATTACHED DOCUMENTATION"
R17+   : ciclo per ogni giorno:
         - row data (es. "02 JANUARY 2025") in col 1
         - row header (TIME, SUPPLIER, CERTIFICATE, CONTRACT, eRSV n., CAR, TRUCK, SPECIAL, ...)
         - N righe transazione (una per veicolo in arrivo)
         - row TOTAL (somma input giornaliero)
         - eventuale row aggregata produzione (kg_to_production, eu_prod, plus_prod, output_eu)
```

### Colonne (22 utili)
| Col | Header | Tipo dato reale |
|-----|--------|----------------|
| 1 | TIME | `time` (HH:MM) |
| 2 | SUPPLIER | text (BIOWASTE, ESENTTIA, ...) |
| 3 | CERTIFICATE | text (cert_number) |
| 4 | CONTRACT | text (contract_code) |
| 5 | eRSV n. | text (formato `NNN/25`) |
| 6 | CAR | numeric kg |
| 7 | TRUCK | numeric kg |
| 8 | SPECIAL | numeric kg |
| 9 | THEOR. VEG. % | numeric (popolato 178/2429) |
| 10 | MANUF. VEG. % | numeric (raro) |
| 11 | Kg TO PRODUCTION | numeric (negativo, = -input) |
| 12 | EU PROD. Kg | aggregato giorno (no per riga) |
| 13 | PLUS PROD. Kg | aggregato giorno (no per riga) |
| 14 | C14 ANALYSIS | **TEXT** (lab name, sample ID, dates) — non bool |
| 15 | Carbon Black Kg | aggregato giorno, valori negativi |
| 16 | Metal scrap Kg | aggregato giorno, valori negativi |
| 17 | H2O % | aggregato giorno, valori negativi |
| 18 | Gas/Syngas % | aggregato giorno, valori negativi |
| 19 | Losses | aggregato giorno, valori negativi |
| 20 | OUTPUT EU Kg | aggregato giorno (mai per riga) |
| 21 | CONTRACT (output) | text |
| 22 | POS No. | text |

---

## 2. Anagrafiche reali estratte

### Suppliers (7)

| Nome | Country | Entries | Kg totali | Note |
|------|---------|--------:|----------:|------|
| ESENTTIA | CO | 533 | 9,193,201 | producer principale |
| SANIMAX | CO | 348 | 5,633,402 | |
| LITOPLAS | CO | 335 | 5,307,916 | |
| CIECOGRAS | CO | 283 | 4,538,836 | |
| BIOWASTE | CO/PL | 229 | 3,025,933 | cert PL21990602701 |
| ≤5 TON | CO | 677 | 2,722,219 | aggregato anonimo small suppliers |
| ECODIESEL | CO/PL | 24 | 325,521 | new in SEP 2025 |
| **TOTALE** | | **2429** | **30,747,028** | |

### Certificates (9)

| Cert number | Suppliers usanti | Note |
|-------------|------------------|------|
| `CO222-00000026` | ESENTTIA, LITOPLAS, SANIMAX, ≤5 TON | shared |
| `CO222-00000027` | CIECOGRAS, ESENTTIA, LITOPLAS, SANIMAX | shared |
| `ES216-20254036` | CIECOGRAS, LITOPLAS, SANIMAX, ≤5 TON | shared |
| `ES216-20268083` | CIECOGRAS, ESENTTIA, LITOPLAS, SANIMAX | shared |
| `PL219-91159801` | ECODIESEL | dedicated |
| `PL21990602701` | BIOWASTE | dedicated |
| `-` | ≤5 TON | placeholder no-cert |
| `SD` | ≤5 TON | self-declaration short |
| `SELF DECL. ISCC` | ≤5 TON | self-declaration full |

### Contracts (5)

| Code | Supplier | Entries |
|------|----------|--------:|
| `BW200224` | BIOWASTE | dedicated |
| `ES400125` | ESENTTIA | dedicated |
| `LP300324` | LITOPLAS | dedicated |
| `SD` | ≤5 TON | self-declaration |
| `-` | CIECOGRAS, ESENTTIA, SANIMAX, ≤5 TON | placeholder |

### eRSV
- 378 numeri unici nel periodo
- formato: `NNN/25` (444 esempi col suffisso `25`)

---

## 3. Volumi 2025 (Jan-Sep)

| Mese | Entries | Input kg |
|------|--------:|---------:|
| 2025-01 | 187 | 3,302,872 |
| 2025-02 | 241 | 3,402,393 |
| 2025-03 | 233 | 3,238,373 |
| 2025-04 | 300 | 3,680,698 |
| 2025-05 | 267 | 3,103,530 |
| 2025-06 | 270 | 3,088,657 |
| 2025-07 | 328 | 3,927,381 |
| 2025-08 | 287 | 3,258,189 |
| 2025-09 | 316 | 3,744,935 |
| **TOT** | **2429** | **30,747,028** |

Recap 2024 (ottobre-dicembre, dalle prime righe sheet JANUARY):
- OCTOBER 2024: 1,351,794 kg input
- NOVEMBER 2024: 3,403,549 kg
- DECEMBER 2024: 3,256,382 kg
- Mass balance 2024 end: **8,011,725 kg**

---

## 4. Anomalie / edge cases

1. **C14 ANALYSIS** schema attuale `BOOLEAN` — realtà = **TEXT free** con:
   - lab names: `SAYBOLT`, `Bureau Veritas`, `Crown Oil`, `OISTE INTERNAL`
   - sample IDs: `NLADM-25-00196-002`, `12011/00110117.5/L/25`
   - date strings: `Date of Sampling : 18-MAR-2025`, `Sample Analysed : ...`, `Date of Report : ...`
   - status: `SAMPLE SHIPPED TO NL`
   - 129 righe popolate, 2300 vuote
2. **theor_veg_pct** popolato solo 178/2429 (= 7%), valore quasi unico `23.0`
3. **eu_prod_kg / plus_prod_kg / output_eu_kg** = **mai per transazione**, solo aggregati giornalieri o mensili (separare in tabella distinta)
4. **carbon_black/metal_scrap/h2o/gas_syngas/losses** = aggregati giorno, **valori negativi** (loss accounting); 168 righe popolate
5. **Multi-input row:** 7 entries con peso > 0 in più di una colonna (CAR + TRUCK simultanei) — possibili errori operatore, da flag
6. **2 righe** con valori non numerici nei pesi
7. **Placeholder cert/contract** `-`, `SD`, `SELF DECL. ISCC` — devono essere pseudo-record validi (sennò FK invalide)
8. **≤5 TON** = pseudo-supplier aggregato (non vero fornitore) — modellare come `is_aggregate=true`

---

## 5. Mismatch DB attuale vs realtà

### Migration `0007_seed_suppliers_certificates.py` = DA RIFARE
Seed attuale è **fake/mock** (EcoTire Colombia, GreenFuel, BioPetrol, Renovar, SustainOil — nomi inventati). Nessuna corrispondenza con dati reali.

### Schema `daily_entries` — modifiche necessarie

| Campo | Attuale | Reale | Azione |
|-------|---------|-------|--------|
| `c14_analysis` | BOOLEAN | TEXT free (lab/sample/date) | **migrazione 0009** ALTER COLUMN TYPE TEXT |
| `c14_value` | NUMERIC(5,2) | usato raramente, valori `0.293`, `0.309` | OK |
| `eu_prod_kg`, `plus_prod_kg`, `output_eu_kg` | NUMERIC su daily_entry | aggregati giorno (mai per riga) | spostare in **`daily_production` separata** o nullable |
| `carbon_black_kg`, `metal_scrap_kg`, `losses_kg` | NUMERIC daily_entry | aggregati giorno, negativi | come sopra |
| `h2o_pct`, `gas_syngas_pct` | NUMERIC(5,2) | valori in kg negativi nel xlsx | rinominare o ridefinire |

### Proposta separazione (raccomandata)

```sql
-- INPUT layer (per transazione/veicolo)
daily_inputs (id, entry_date, entry_time, supplier_id, certificate_id, contract_id,
              ersv_number, car_kg, truck_kg, special_kg, total_input_kg GENERATED,
              theor_veg_pct, manuf_veg_pct, c14_text, c14_value,
              source_file, source_row, audit fields, deleted_at)

-- PRODUCTION layer (aggregato per giorno)
daily_production (id, prod_date PK, kg_to_production, eu_prod_kg, plus_prod_kg,
                  carbon_black_kg, metal_scrap_kg, h2o_kg, gas_syngas_kg,
                  losses_kg, output_eu_kg, contract_ref, pos_number,
                  audit fields)
```

Oppure (più semplice, una sola tabella) mantieni `daily_entries` con tutti i campi nullable e usa un flag `entry_type` (`input` | `production_summary`).

---

## 6. Action plan

1. **Migration 0009** — fix `c14_analysis` BOOLEAN → TEXT + rename `c14_value` → `c14_pct` (opzionale)
2. **Migration 0010** — sostituisce seed 0007 con anagrafiche reali:
   - 7 suppliers (idempotente: ON CONFLICT DO NOTHING)
   - 9 certificates (incl. placeholder `-`/`SD`/`SELF DECL. ISCC` con flag `is_placeholder=true`)
   - 5 contracts (idem placeholder)
   - **Junction table** `supplier_certificates` per relazione N:N (cert condivisi tra suppliers)
3. **Script `scripts/ingest_xlsx.py`**:
   - leggi tutti gli sheets, parsing layout misto (date row + header + transactions + total)
   - dry-run mode: report errori (multi-input, valori non numerici, supplier sconosciuto)
   - bulk insert in `daily_entries` con `source_file` + `source_row`
   - skippa righe TOTAL e righe aggregato giornaliero (vanno in `daily_production` separato)
4. **Schema decisione:** scegliere tra single-table o split inputs/production — incide su frontend reports

---

## 7. Riferimenti

- File sorgente: `/tmp/girardot_enero_2025.xlsx` (459 KB, 9 sheets)
- Estrazione JSON: `/tmp/girardot_entries.json` (2429 entries)
- BLUEPRINT: `BLUEPRINT.md`
- Context AgentOS: `docs/agentos-context.md`
- Migration seed da rifare: `backend/alembic/versions/0007_seed_suppliers_certificates.py`
