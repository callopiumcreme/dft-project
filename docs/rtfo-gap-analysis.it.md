# Analisi dei Gap RTFO — DFT Project vs requisiti UK RTFO

> Data: 2026-05-12
> Fonte DFT: `BLUEPRINT.md` + `backend/app/models/` + 3 migration alembic (0001 schema, 0002 seed, 0003 mv)
> Fonte RTFO: `docs/rtfo-essential-guide.md` (DfT essential guide, scaricata il 2026-05-12)
> Impianto: Girardot (Colombia) — pirolisi di rifiuti plastici / pneumatici / gomma → liquido + char + gas
> Schema di certificazione attualmente tracciato: **solo ISCC EU** (`Certificate.scheme` default `"ISCC EU"`)

---

## 0. Sintesi esecutiva

Il sistema DFT è oggi un **tracker di mass-balance input/output** progettato attorno alla contabilità dello schema volontario **ISCC EU**. Registra input giornalieri di feedstock (kg auto/camion/special), output di pirolisi (EU prod / plus prod / carbon black / metal scrap / H2O / syngas / perdite), certificati e contratti fornitori, più campi C14 di quota biogenica sugli input.

L'**RTFO** UK è un regime di obbligo parallelo che emette **RTFC** negoziabili per litro di carburante rinnovabile sostenibile *fornito al trasporto UK*, con una traccia separata **dRTFC** per i **Development Fuels** (RFNBO, RCF, rifiuti double-counting) che porta un sub-target di 1,619% sopra l'obbligo principale del 14,054% (valori 2025).

Perché l'impianto di Girardot partecipi all'RTFO (assumendo che l'olio di pirolisi raggiunga il trasporto UK tramite un fornitore registrato), il sistema DFT necessita di aggiunte in **sei aree**: (1) intensità carbonica GHG per batch, (2) classificazione feedstock secondo la lista RTFO, (3) inventario RTFC, (4) export reporting in formato ROS, (5) ledger di carry-over + buy-out, (6) workflow del verificatore. Nessuno di questi esiste oggi. Il core di mass-balance, il registro fornitori/certificati e l'audit log già in essere sono fondamenta riutilizzabili — non vanno sostituiti, solo estesi.

Punto cruciale: **l'output di pirolisi da plastica / pneumatici / gomma è molto probabilmente classificato come Recycled Carbon Fuel (RCF) sotto RTFO**, che vale **1 dRTFC per litro** (non 2×, niente double-count biogenico) e usa la **metodologia GHG controfattuale Annex D** — fondamentalmente diversa dall'approccio ISCC EU basato su contenuto biogenico + lifecycle. Questo plasma la maggior parte delle raccomandazioni sotto.

---

## 1. Contesto regolatorio

| | DFT oggi | RTFO |
|---|---|---|
| Schema | ISCC EU (volontario, EU RED II) | UK RTFO (obbligo di legge) |
| Unità di contabilità | kg di feedstock + kg di prodotto | litri (o kg-equiv con moltiplicatori) di carburante *fornito* al trasporto UK |
| Trigger | Mass-balance bookkeeping continuo | Fornitore ≥ 450.000 L/anno di carburante rilevante in UK |
| Evidenza | Dichiarazioni di sostenibilità + audit ISCC | Assegnazione RTFC via ROS + verificatore indipendente + controlli mirati DfT |
| Oggetto della compliance | Quota bio / risparmio GHG del batch fisico | Obbligo annuale in RTFC (principale + sub-target dev), riconciliato entro 15 settembre dell'anno successivo |
| Moneta dell'obbligo | n/a (schema dichiarativo) | RTFC, dRTFC, o buy-out in contanti (£0,50 / £0,80 per cert mancante) |

L'impianto DFT sta sul lato *produzione* di questa catena. Se l'output di pirolisi viene esportato a un fornitore UK obbligato, l'RTFC viene **assegnato al fornitore UK** al punto di accisa (o punto di alt-assessment), ma il fornitore necessita dell'evidenza upstream di sostenibilità + GHG che DFT produce.

---

## 2. Classificazione RTFO probabile dell'output Girardot

Da `docs/rtfo-essential-guide.md` §6:

- **RCF (Recycled Carbon Fuel):** carburante prodotto da un rifiuto fossile che non può essere riciclato, riusato o prevenuto, E designato come feedstock rilevante dalla LCF Delivery Unit. Usa **metodologia GHG controfattuale Annex D**. Assegnato **1 dRTFC per litro** equivalente. Niente double-count.
- **Rifiuto/residuo double-counting (dRTFC generale):** tipicamente biogenico — olio da cucina usato, grassi animali, residui agricoli. **2× dRTFC per litro**.

**Pneumatici** a fine vita, **rifiuti plastici misti** e **gomma sintetica** sono di origine fossile → **percorso RCF, non double-counting biogenico**, a meno che l'input non sia genuinamente biomassa (es. lignina, gomma derivata da biomassa). Oggi DFT ha `c14_value` su `daily_inputs` (analisi C14 che indica la quota biogenica) — è il campo che meccanicamente dice biogenico vs fossile per ogni camion.

**Implicazione:** per RTFO, due flussi di prodotto devono essere tracciati separatamente nel mass-balance:
1. **Output a quota biogenica** (proporzionale alla frazione bio confermata da C14 sugli input) → potenzialmente **2× generale o dRTFC** a seconda del feedstock.
2. **Output a quota fossile** (la maggioranza per pirolisi di plastica/pneumatici) → **RCF, 1 dRTFC** per litro, GHG Annex D.

DFT oggi ha `theor_veg_pct` + `manuf_veg_pct` + `c14_value` per camion ma nessuno split di prodotto downstream per batch. L'olio di pirolisi esce dall'impianto come un unico flusso; lo split rilevante per RTFO oggi non viene preservato.

---

## 3. Inventario gap (campo per campo)

### 3.1 Classificazione feedstock

| Cosa serve a RTFO | DFT oggi | Gap |
|---|---|---|
| Feedstock corrispondente alla **List of Feedstocks** (pre-approvata) o valutazione pendente | solo `suppliers` — nessuna entità feedstock | **MANCANTE** — nessuna tabella `feedstock`, nessun link feedstock→input row |
| Tipo feedstock: rifiuto / residuo / coltura energetica dedicata / biomassa / fossil-waste-RCF | implicito nel nome fornitore | **MANCANTE** — nessun enum, nessun tag per riga |
| Eleggibilità al double-counting | n/a | **MANCANTE** |
| Designazione RCF da LCF Delivery Unit | n/a | **MANCANTE** |

**Raccomandazione:** nuova tabella `feedstocks` + FK su `daily_inputs.feedstock_id`. Colonna enum per `rtfo_class` ∈ `{relevant_crop, general_waste, double_counting_waste, rcf, rfnbo, ineligible}`. Seed con la *List of Feedstocks* pubblicata.

### 3.2 Intensità carbonica GHG

| Cosa serve a RTFO | DFT oggi | Gap |
|---|---|---|
| CI per batch in gCO₂eq/MJ (o per litro) | non tracciato | **MANCANTE** |
| ≥ 55–65% di risparmio GHG vs controfattuale fossile (baseline 94 gCO₂eq/MJ per biocarburanti) | non applicato | **MANCANTE** |
| Metodologia controfattuale Annex D per RCF | non implementata | **MANCANTE** |
| Integrazione con output DfT Carbon Calculator | nessuna | **MANCANTE** |

**Raccomandazione:**
- Nuova tabella `ghg_calculations` chiavata su `(daily_production_id, methodology_version)` che memorizza CI input per stadio (coltivazione/raccolta, processing, trasporto), CI finale, % di risparmio vs controfattuale, e un enum `methodology` ∈ `{red_ii_default, red_ii_actual, annex_d_counterfactual}`.
- Colonna `daily_production.ghg_calculation_id` (nullable).
- Prima iterazione solo import: accetta CI da spreadsheet → memorizza + valida soglia → blocca applicazione RTFC se sotto soglia.

### 3.3 Inventario RTFC

| Cosa serve a RTFO | DFT oggi | Gap |
|---|---|---|
| Certificati emessi per litro/kg-eq | n/a (ISCC è uno schema dichiarativo, non un cert negoziabile per unità) | **TOTALMENTE MANCANTE** |
| Classe RTFC: generale / coltura rilevante / dRTFC | n/a | **MANCANTE** |
| Eventi award / redeem / sell / buy-out | n/a | **MANCANTE** |
| 25% carry-over da periodo precedente, solo annuale singolo | n/a | **MANCANTE** |

**Raccomandazione:** nuovo modulo `rtfc_ledger` con tabelle:
- `rtfc_batch(id, obligation_period_year, class enum, litres_eligible, dRTFC_qty, RTFC_qty, ghg_calculation_id, daily_production_id, status)`
- `rtfc_event(id, batch_id, event_type enum {awarded, redeemed, sold, bought, carried_over, bought_out}, qty, counterparty, price_per_cert, event_date)`
- View `rtfc_balance(obligation_period_year, class)` per posizione obbligo live.

### 3.4 Registro fornitori & verificatori

| Cosa serve a RTFO | DFT oggi | Gap |
|---|---|---|
| Identità del verificatore indipendente per applicazione RTFC | non tracciata | **MANCANTE** |
| Link a schema volontario riconosciuto (ISCC EU è una via) | campo `Certificate.scheme` — già stringa | **PARZIALE** — tipizzato stringa, nessun enum, nessun check sulla lista DfT riconosciuta |
| Buyer = fornitore UK obbligato | tabella suppliers è *upstream* (fornitori di materia prima), non off-taker downstream | **MANCANTE** — nessuna entità `customer` / `off_taker` |

**Raccomandazione:**
- Nuova tabella `off_takers` per i fornitori UK downstream che ricevono l'olio di pirolisi.
- Nuova tabella `verifiers` + FK `rtfc_batch.verifier_id`.
- Migrare `Certificate.scheme` a enum-constrained `{ISCC EU, REDcert, 2BSvs, RSB, KZR INiG, ...}` allineato alla lista DfT riconosciuta.

### 3.5 Export reporting in formato ROS

| Cosa serve a RTFO | DFT oggi | Gap |
|---|---|---|
| Sottomissione volumi via **ROS** (RTFO Operating System) validata contro dati accise HMRC | solo import xlsx; nessun tracking di fornitura al trasporto UK | **MANCANTE** |
| Tracciabilità per batch da feedstock → fornitura finale al trasporto UK | mass-balance finisce al cancello impianto | **MANCANTE ULTIMO MIGLIO** |
| Bundle artefatto di verifica indipendente (PDF + dati di supporto) | generazione cert PDF ISCC pianificata | **PARZIALE** — adattare il generatore PDF pianificato a produrre anche report ROS-compatibile |

**Raccomandazione:**
- Definire una view `rtfo_export` che produce la forma dati attesa da ROS (per schema ROS pubblicato — serve fetch separato).
- Job di export versionati nell'audit log; ri-eseguibili idempotenti per restatement.

### 3.6 Criteri di sostenibilità (terreno / foresta / soil carbon)

| Cosa serve a RTFO | DFT oggi | Gap |
|---|---|---|
| Criteri sul terreno (no conversione di aree ad alta biodiversità / alto stock di carbonio) | non tracciati | **MANCANTE** — ma rilevante solo per feedstock biogenici; per RCF da rifiuto fossile questa sezione non si applica |
| Criteri forestali | non tracciati | **MANCANTE** (n/a per RCF plastica/pneumatici) |
| Soil carbon (rifiuti agricoli) | non tracciato | **MANCANTE** (n/a per RCF plastica/pneumatici) |

**Raccomandazione:** aggiungere un `feedstock.sustainability_attestation_url` per i casi in cui il feedstock È biogenico (pellet di lignina, char da biomassa). Per il flusso RCF puro questo gap è benigno.

### 3.7 Ciclo di vita dell'obbligo & scadenze

| Cosa serve a RTFO | DFT oggi | Gap |
|---|---|---|
| Periodo di obbligo calendario 1 gen → 31 dic | DFT opera su anno solare via `prod_date` naturale | **PARZIALE** — usabile ma nessuna entità `obligation_period` esplicita |
| Reminder scadenza 15 settembre dell'anno successivo | nessuno | **MANCANTE** — nessun sottosistema reminder/notifiche |
| Opzione buy-out a £0,50 / £0,80 per cert mancante | n/a | **MANCANTE** — serve ledger finanziario |

---

## 4. Cosa DFT *già* copre utilmente

Questi elementi vanno estesi ma non riprogettati:

- **`daily_inputs` + `daily_production` mass-balance** con materialized view — lo scheletro kg-in / kg-out per qualsiasi schema di sostenibilità.
- **Registro fornitori + supplier_certificates many-to-many** — abbastanza generico da ospitare schemi volontari riconosciuti RTFO accanto a ISCC EU.
- **`audit_log`** — registra già chi/quando/cosa per daily_entries; si estende naturalmente ad award/redeem/sell di RTFC.
- **Tracciabilità `source_file` + `source_row`** — ogni riga input/produzione puntabile all'xlsx originale; un'ispezione di verificatore RTFO lo apprezzerebbe.
- **Disciplina del soft delete (`deleted_at`)** — niente riscritture distruttive della storia; postura richiesta per audit ISCC e ugualmente per verifica RTFO.
- **Campi analisi C14** (`c14_value`, `c14_analysis`) — evidenza fisica diretta della quota biogenica, utile sia per ISCC sia per qualsiasi argomento di split biogenico/RCF sotto RTFO.

---

## 5. Fasatura implementativa raccomandata

**Fase 1 — Read-only readiness (nessuna fornitura UK ancora, solo prep)**
1. Nuova tabella `feedstocks` + FK da `daily_inputs`. Seed dalla RTFO List of Feedstocks.
2. Storage GHG CI per batch (`ghg_calculations`) — solo upload manuale.
3. Enum scheme su `certificates`.

**Fase 2 — Se/quando un off-taker UK obbligato RTFO si aggancia**
4. Tabelle `off_takers` + `verifiers`.
5. Ledger `rtfc_batch` + `rtfc_event`.
6. View carry-over (25%, solo anno singolo in avanti).

**Fase 3 — Reporting + automazione**
7. Formato export ROS + scheduler.
8. Reminder scadenza 15-set + ledger buy-out.
9. Bundle PDF verificatore (estende generatore PDF ISCC pianificato).

**Fase 4 — Automazione GHG**
10. Implementare metodologia controfattuale Annex D per il flusso RCF nel codice; integrazione con DfT Carbon Calculator (import CSV o API se disponibile).

---

## 6. Non-goal / esplicitamente fuori scope

- Implementare logica RTFO *prima* che esista un off-taker UK obbligato. Costruire prematuramente rischia divergenza dall'eventuale schema ROS e dagli aggiornamenti della metodologia Annex D.
- Sostituire il tracking ISCC EU. ISCC EU resta lo schema volontario primario usato; RTFO sta *accanto* per il carburante instradato al trasporto UK.
- Campi criteri forestali / terreno / soil oltre un URL di attestazione free-form, finché un feedstock biogenico non entra effettivamente in impianto.

---

## 7. Domande aperte per il cliente

1. Qualche off-taker attuale o di breve termine è un fornitore UK obbligato (≥ 450 kL/anno al trasporto UK)?
2. Quale frazione dell'output Girardot è quota biogenica vs quota fossile via C14? (Determina l'allocazione di classe dRTFC.)
3. Il mix feedstock plastica/pneumatici/gomma è stato formalmente designato dalla LCF Delivery Unit come feedstock RCF-eleggibile? Se no, la richiesta di designazione è precondizione per qualsiasi assegnazione RTFC.
4. L'off-taker contratta su base *fisica* (segregata) o *mass-balance*? RTFO accetta mass-balance, ma i flag GHG per batch e classe devono seguire il volume.

---

## 8. Manutenzione documento

- Rileggere la guida sorgente a ogni aggiornamento annuale della percentuale di obbligo (prossimo: valori 2026, pubblicati prima del periodo di obbligo 2026).
- Cross-check contro `docs/rtfo-essential-guide.md` dopo qualsiasi revisione della essential-guide DfT.
- Tenere questo doc gap allineato con le migration di schema: ogni nuova migration a supporto RTFO dovrebbe referenziare la sezione gap che chiude.
