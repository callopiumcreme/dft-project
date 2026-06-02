# DFT-C1 — Ricontrollo Audit Interno

**Data:** 2026-06-01
**Autore:** Interno (lato FMS / sistema dati)
**Ambito:** Rivalutazione dello stato audit DfT C1 ad oggi, riconciliando l'auto-audit
interno (16 criteri, ultima chiusura Round-5 / 2026-05-27) con la **lettera formale
di rigetto DfT del 9-Mar-2026** e le 5 domande di follow-up di Deeba Rehman.
Consignment in ambito: **DEL-CRW-2025-2**. Finestra: **Gen–Ago 2025**. Unico buyer:
Crown Oil UK (Europa esclusa). Buyer byproduct: Conquer Trade (DEV-P200).

> **Disciplina di metodo.** Ogni dato quantitativo qui sotto è stato verificato
> direttamente contro il DB di **produzione** e il repo il 2026-06-01 prima di essere
> scritto (`feedback_verify_before_report`). Dove un fatto è upstream / supply-chain e
> non può essere risolto dal nostro sistema, è marcato esplicitamente come
> **fuori-sistema** — non dichiarato risolto.

---

## 0. Verdetto esecutivo

**Realtà a due binari. Sono in disaccordo, e il disaccordo è il titolo.**

- **Binario interno (il nostro sistema dati):** **solido e in miglioramento.**
  L'auto-audit era PASS al Round-5 (15/16, 1 deferred) su alembic `0041`. Prod è ora a
  `0047` — sei migration di pulizia/schema oltre l'ultimo verdetto, più due feature UI
  rilasciate (PDF supply-data-sheet, colonna Doc ID) che migliorano la tracciabilità
  dell'evidenza. Il mass balance chiude (Mar–Ago = 0.0000%, Gen/Feb = carry-over
  simmetrico documentato). I log di produzione kg→litri **esistono e sono pienamente
  popolati** (194/194 righe).

- **Binario esterno (regolatore DfT):** **NON superato.** La lettera del 9-Mar-2026 ha
  **rigettato** la submission e DfT ha **cancellato 5 bundle RTFO** il 13-Mar-2026. La
  deadline di re-submission ROS (14-Mag-2026) è **PASSATA**. I quattro finding DfT sono
  per lo più **fatti di certificazione supply-chain upstream** (certificazione ISCC dei
  punti di raccolta degli pneumatici a fine vita; registrazione tyre-handling dei
  feedstock provider) che un sistema dati interno pulito **non può sistemare da solo**.

**In sintesi:** il "PASS" interno è **necessario ma non sufficiente**. Un auto-audit
verde significa che il nostro ledger è coerente e difendibile; **non** significa che
DfT accetterà la catena. I blocker rimanenti sono prevalentemente **fuori-sistema** e
richiedono azione di Crown Oil + supplier, non altre migration.

---

## 1. Delta di stato dal Round-5 (2026-05-27 → 2026-06-01)

| Asse | Round-5 | Ora (2026-06-01) | Verificato |
|------|---------|------------------|------------|
| Alembic head (prod) | `0041` | **`0047_c14_certificate_schema`** | `alembic_version` su prod |
| Certificati attivi | — | **15** (6 con PDF, 6 in-finestra senza, 3 placeholder) | `certificates WHERE deleted_at IS NULL` |
| Supplier attivi | — | **8** | `suppliers WHERE deleted_at IS NULL` |
| Daily inputs | — | **2047** righe, 2025-01-02 → 2025-08-30 | `daily_inputs` |
| Daily production | 194 giorni | **194** righe, tutte con litri | `daily_production` |
| Product purchases | — | **51** | `product_purchases` |
| Byproduct sales | — | **8** | `byproduct_sale` |
| Note cert AUDIT-MISMATCH | — | **2** | `certificates.notes LIKE '%AUDIT-MISMATCH%'` |

**Migration aggiunte dall'ultimo verdetto:**

- `0042_d17_cosmetic_fixture_cleanup` — igiene cosmetica / fixture.
- `0043_byproduct_sale_pdf_ref` — link byproduct sale → riferimento PDF.
- `0044_retire_ecogras_2025_cert` — soft-deprecate cert ECOGRAS 2025 (ES216-20254036).
- `0045_le5ton_cert_drift_cleanup` — pulizia drift bucket self-decl LE5TON (pattern NULL
  canonico, `project_le5ton_no_pos`).
- `0046_product_purchases_schema` — modello product-purchases (alimenta supply-data-sheet).
- `0047_c14_certificate_schema` — schema certificato C14 (head corrente).

**Feature rilasciate in prod dall'ultimo verdetto:**

- **Supply Data Sheet** (PDF proforma) — `templates/reports/proforma_invoice.html`,
  renderizzato per `product_purchase`, esplicitamente **"non una fattura fiscale"**
  (foglio di presentazione dati onorato dalla fattura commerciale del supplier). Render
  verificato `200 application/pdf %PDF`.
- **Colonna Doc ID** in `/app/inputs` — sha256(16-hex) della riga eRSV canonica, 1:1 con
  l'header del PDF eRSV stampato; apre lo stesso modal eRSV del mass-balance. Sostituisce
  la colonna eRSV grezza. Verificata via Playwright su prod.

---

## 2. Ricontrollo 16 criteri interni (riporto dal Round-5)

Round-5 era **15 PASS / 0 FAIL / 1 DEFERRED**. Ricontrollo di oggi: tutti i 15 criteri
PASS restano strutturalmente soddisfatti a `0047` (nessuna regressione trovata; il mass
balance chiude ancora, nessun input orfano, supplier/cert legacy ancora ritirati). **C16
(schema driver / cedula / targa) resta DEFERRED** — colonne ancora assenti, ancora in
attesa input cliente DRIVERS (B1–B4). Invariato e resta **non un blocker audit per il
bundle Crown Oil** secondo la definizione del Round-5.

**Netto:** la matrice interna tiene. Nessun nuovo FAIL interno introdotto da `0042–0047`.

---

## 3. Lettera di rigetto DfT 9-Mar-2026 — riconciliazione finding per finding

Finding verbatim (fonte: `docs/audit-dft-c1-deeba-realign/2026-05-29-morning-pending-notes.md`).

### F1 — Certificazione ISCC dei punti di raccolta pneumatici
> "the submitted evidence did not sufficiently demonstrate that the EoL tyres were
> supplied by ISCC certified collection points … DfT do not therefore consider any of
> the supply chain to be ISCC certified"

- **Severità:** 🔴 massima. Invalida la catena alla radice.
- **Stato in-sistema:** deteniamo certificati supplier (15 record; **tutti i PDF dei cert
  reali presenti su disco**, inclusi rinnovi 2025 e PYRCOM; 3 placeholder by-design =
  LE5TON self-decl) e narrativa chain-of-custody post-0044/0045. La prima stesura segnalava
  "6 PDF mancanti": **errore di lettura colonna `pdf_ref` non backfillata**, ritirato — vedi
  W1.
- **Gap fuori-sistema:** se i **punti di raccolta** che alimentano i supplier di
  pneumatici siano essi stessi ISCC certificati **non è un fatto che il nostro DB possa
  fabbricare**. Richiede il certificato di scope ISCC upstream del supplier che nomina i
  punti di raccolta, o equivalente accettabile da DfT. **Crown Oil + supplier devono
  fornirlo.**
- **Azione:** ottenere PoS / scope cert ISCC che coprano esplicitamente i punti di
  raccolta pneumatici a fine vita per i supplier lato pneumatici (KALTIRE / BOLDER /
  EFFICIEN / PYRCOM). I PDF dei certificati supplier sono **già a fascicolo**; il gap è lo
  scope upstream che nomina i punti di raccolta, non il documento cert in sé.

### F2 — Record feedstock incompleti + "log produzione a litri non forniti"
> "Records of feedstock material received were incomplete or inconsistent; production
> logs detailing conversion to litres were not provided despite being requested"

- **Severità:** 🟠 → **in gran parte RISOLTO in-sistema.**
- **parte litri:** **RISOLTA.** `daily_production` ha `litres_eu` + `litres_plus`
  popolati su **194/194** righe (Σ EU = 9.502.019 L, Σ PLUS = 11.815.843 L, verificato
  oggi). La MV `mv_mass_balance_monthly` espone `eu_prod_litres / plus_prod_litres /
  total_prod_litres` per mese. La lettera fotografava uno stato **pre-Sprint-2**; i log
  di conversione ora esistono e sono interrogabili.
- **parte record-feedstock:** **parzialmente aperta.** I daily input sono completi e
  senza orfani (2047 righe, Gen2–Ago30, FK supplier+cert pulite). Ma il **tipo/materiale
  feedstock non è modellato come colonna strutturata** — `suppliers` non ha
  `feedstock_type`, e non c'è classificazione materiale per-riga (Sprint α "modello
  feedstock" è DEFERRED post-audit). L'"inconsistente" di DfT probabilmente si riferisce
  al **pivot Gen plastica/organici → Feb ELT** (`project_feedstock_elt`), che è un mix
  storico reale, non un difetto dati — ma serve una **narrativa chiara**, non un cambio
  schema.
- **Azione:** (a) ridichiarare che i log litri ora sono forniti (rigenerare l'export);
  (b) scrivere la narrativa mix-feedstock per Gen vs Feb–Ago esplicitamente.

### F3 — Feedstock provider non registrati per gestire pneumatici
> "no evidence that most feedstock providers associated with the fuel were registered to
> handle tyres"

- **Severità:** 🔴 alta, **fuori-sistema.**
- **Stato in-sistema:** 8 supplier attivi — lato pneumatici = **KAL TIRE (CL), BOLDER
  (US), EFFICIEN (US), PYRCOM (CO)**; lato plastica/organici = **LITOPLAS, BIOWASTE,
  ESENTTIA (tutti CO)** + **LE5TON** (aggregato self-decl ≤5 TON, CO).
- **Rischio mismatch (aperto):** lo skeleton folder ANLA DFTEN-108
  (`04_feedstock_provider_authorisations/`) copre attualmente il trio
  **plastica/organici** (Litoplas/Biowaste/Esenttia). DfT chiede registrazione
  **tyre-handling**. **Lo scope folder e l'ask potrebbero non allinearsi** — è l'ipotesi
  irrisolta del 2026-05-29 (item A) e **ancora non chiusa**.
- **Azione:** confermare con Crown Oil/Paolo **quali supplier sono gli effettivi provider
  di pneumatici a fine vita in ambito per DEL-CRW-2025-2**, poi raccogliere
  l'autorizzazione tyre-handling di ciascuno (es. permesso ANLA / ambientale che nomina
  pneumatici). È raccolta documenti, non codice.

### F4 — Inconsistenze sito produzione (foto / capacità / date avvio)
> "production site images, capacity of the production facility and production start dates"
> [inconsistente]

- **Severità:** 🟡 media, **fuori-sistema / documentale.**
- **Stato in-sistema:** niente nel DB parla di foto impianto / capacità di targa / date
  di commissioning. Vivono nel bundle narrativo.
- **Azione:** assemblare una singola scheda-fatti sito produzione coerente (foto +
  capacità + data avvio) e assicurarsi che ogni documento del bundle citi gli **stessi**
  numeri. Pura coerenza documentale.

---

## 4. 5 domande di follow-up di Deeba — stato

| # | Domanda | Stato | Owner |
|---|---------|-------|-------|
| 1 | Ciclo end-to-end feedstock → fuel (origine/punto raccolta → ricevuto → conversione) | 🟡 parziale — ledger interno (inputs→production→litri→consignment) esiste; **l'origine punto-raccolta** è il gap | FMS + doc supplier |
| 2 | Rivedere diagramma 3 supply chain (allegato) | ⏳ in attesa artefatto cliente | Crown Oil / Paolo |
| 3 | Litoplas/Biowaste/Esenttia sono punti di raccolta? Se no, dare quelli reali | 🔴 aperto — sono supplier plastica/organici, **non punti raccolta pneumatici**; vanno nominati i punti reali | doc supplier |
| 4 | Litoplas/Biowaste/Esenttia sono TUTTI i feedstock provider 2025? | 🔴 serve risposta onesta — **no.** Lato pneumatici (KAL TIRE/BOLDER/EFFICIEN/PYRCOM) anche nel 2025; Gen era plastica/organici, Feb+ ELT | conferma cliente |
| 5 | Record 2024 — includere punto raccolta/origine se mancante | ⚪ fuori finestra audit (Gen–Ago 2025) — chiarire se il 2024 è in ambito | Crown Oil |

**Q3 + Q4 sono il nocciolo.** Rispondervi sinceramente espone il pivot Gen-plastica →
Feb-pneumatici e obbliga a nominare i punti di raccolta pneumatici reali. È la stessa
radice di F1/F3.

---

## 5. Punti forti

- **S1 — Il mass balance è auditabile e chiude.** Chiusura Mar–Ago = **0.0000%**; la
  deviazione Gen/Feb è un **carry-over simmetrico documentato di ±339.865 kg** (Gen
  −10.05%, Feb +12.83% — stessi kg, denominatori diversi), non un difetto
  (`project_jan_feb_stock_carryover`). 8 mesi, 194 giorni produzione, nessun `prod_date`
  duplicato, nessun input orfano.
- **S2 — I log di conversione kg→litri ora esistono (l'ask litri di F2 è rispondibile).**
  194/194 righe produzione hanno litri; la MV espone litri mensili. Smentisce
  direttamente il finding "non forniti" per lo stato corrente.
- **S3 — Igiene dati pulita e monotona.** Sei migration additive (0042–0047) dall'ultimo
  verdetto, ciascuna con provenance audit-log; supplier/cert legacy soft-deprecati (mai
  hard-delete); pattern NULL canonico LE5TON imposto.
- **S4 — Tracciabilità evidenza migliorata nell'UI.** La colonna Doc ID rende ogni riga
  eRSV cliccabile fino al suo PDF firmato (hash 1:1 con l'header stampato); il
  supply-data-sheet dà un artefatto quantità per-acquisto pulito, **non-fiscale**, che
  non si maschera da fattura (importante per l'onestà dell'audit).
- **S5 — Disciplina soft-delete + audit-log tiene.** CHECK `audit_log.action` rispettato
  ovunque (estensioni schema taggate come `action='update'` + `new_values.kind`); nessun
  dato compliance storico riscritto in silenzio (`project_iscc_audit_safety`).
- **S6 — Topologia buyer singola e pulita.** Crown Oil = unico buyer DEV-P100 (Europa
  esclusa); Conquer = unico buyer byproduct DEV-P200. Nessuna attribuzione multi-buyer
  ambigua da difendere.

## 6. Punti deboli

- **W1 — RITIRATA. Falso positivo da colonna DB** (rettifica 2026-06-01). La prima stesura
  segnalava "6 certificati ISCC in-finestra senza PDF" come gap interno sfruttabile su F1.
  **Errato.** Quei 6 (`CO222-00000026`, `CO222-00000027`, `ES216-20249051`,
  `US201-120372025`, `US201-138762025`, `US201-158772025`) risultavano senza PDF solo
  perché la **colonna `certificates.pdf_ref` non era backfillata**. I **file PDF esistono
  tutti** su disco (`/data/certificates/supplier-q3/`), inclusi i rinnovi 2025 e PYRCOM, e
  sono serviti dal frontend. **Nessun gap di evidenza PDF.** Tutti i fornitori di gomma
  hanno cert con PDF per l'intera finestra Gen–Ago 2025; i tre placeholder (`-`, `SD`,
  `SELF DECL. ISCC`) sono LE5TON self-decl, vuoti by-design (`project_le5ton_no_pos`).

  **Residuo reale (severità bassa):** la colonna `pdf_ref` va allineata ai 6 file già
  presenti — **igiene dati, non documento mancante** (`feedback_backfill_after_migration`).
  Lezione: verificare il file su disco, non il proxy-colonna. **W1 non contribuisce più a
  F1.** Il colpo su F1 resta solo upstream (vedi §3 F1: scope ISCC punti di raccolta).
- **W2 — Il materiale feedstock non è modellato.** Nessun `feedstock_type` su
  `suppliers`, nessuna classe materiale per-input. La realtà Gen-plastica/Feb-pneumatici
  vive solo nella prosa. DfT lo legge come "inconsistente" (F2). Sprint α lo
  sistemerebbe ma è DEFERRED — quindi per **questa** submission va coperto con narrativa.
- **W3 — Lo scope folder ANLA potrebbe non allinearsi all'ask DfT.** La folder copre il
  trio plastica/organici; DfT vuole registrazione **tyre**-handling (F3). Irrisolto dal
  2026-05-29. Rischio: consegniamo autorizzazioni per i supplier sbagliati.
- **W4 — I finding più duri sono fuori-sistema e dipendono da terze parti.** F1
  (ISCC punto-raccolta) e F3 (registrazione tyre-handling) **non** possono essere chiusi
  da noi. Dipendono da Crown Oil + supplier che producono documenti upstream reali.
  Prontezza interna ≠ prontezza submission.
- **W5 — Deadline già passate.** Deadline re-submission ROS **14-Mag-2026 PASSATA**; 5
  bundle **cancellati il 13-Mar-2026**. Il percorso di re-submission/la relazione devono
  essere riaperti da Crown Oil con DfT — non controlliamo quella timeline.
- **W6 — Il "PASS" interno rischia falsa fiducia.** Il verde auto-audit può essere
  frainteso come "audit vinto". Certifica solo la coerenza del ledger. **È la failure
  mode del 2026-05-29** (dichiarare chiusura senza verificare lo scope). Tenere i due
  binari esplicitamente separati in ogni comunicazione cliente.
- **W7 — La chiusura mass-balance è derivata dal modello, non misurata
  indipendentemente.** Mar–Ago = esattamente 0.0000% perché l'output è derivato
  dall'input dal modello. Non un errore per l'audit corrente, ma **non** è una
  riconciliazione indipendente — se DfT chiede output misurato indipendentemente, c'è un
  gap di narrativa.
- **W8 — DEL-CRW-2025-1 non ha catena upstream ricostruibile** (pre-FMS v1.0,
  `project_del_crw_2025_1_out_of_scope`). Ok **finché DfT concorda che lo scope =
  solo DEL-CRW-2025-2.** Se lo scope si allarga, diventa un buco.

---

## 7. Registro rischi (item aperti, prioritizzati)

| Pri | Item | Binario | Blocker per re-submission? |
|-----|------|---------|----------------------------|
| P0 | F1 — Certificazione ISCC punti raccolta pneumatici | fuori-sistema | **SÌ** |
| P0 | F3 — Registrazione tyre-handling dei supplier pneumatici reali | fuori-sistema | **SÌ** |
| P0 | W5 — Deadline ROS passata; Crown Oil deve riaprire con DfT | fuori-sistema | **SÌ (processo)** |
| P3 | W1 — RITIRATA (falso positivo colonna `pdf_ref`; PDF tutti presenti) | in-sistema | no (solo backfill colonna) |
| P1 | W3 — Allineamento scope folder ANLA (Q3/Q4) | misto | SÌ se supplier sbagliati |
| P2 | Narrativa feedstock F2 (Gen plastica → Feb pneumatici) | in-sistema (prosa) | parziale |
| P2 | F4 — Coerenza scheda-fatti sito produzione | documentale | media |
| P3 | C16 schema driver/cedula | in-sistema | no (deferred, side-track Conquer) |

---

## 8. Azioni raccomandate prima di qualsiasi re-submission

**In-sistema (possiamo farlo, LOCAL prima, deploy solo su parola esplicita):**

1. **Backfill colonna `pdf_ref`** ai 6 file PDF già presenti su disco (igiene dati; W1 era
   un falso positivo — i PDF ci sono). Nessun documento da recuperare.
2. **Rigenerare l'export litri** per DEL-CRW-2025-2 ed etichettarlo chiaramente come "log
   di conversione produzione (kg→litri)" che DfT diceva mancante (F2).
3. **Scrivere la narrativa mix-feedstock** (Gen plastica/organici → Feb–Ago ELT), citando
   le date dei daily-input — trasforma l'"inconsistente" di DfT in "pivot intenzionale,
   ecco le date".
4. **Risolvere le 2 note cert AUDIT-MISMATCH** o documentare perché restano
   (`project_iscc_audit_safety` — mai riscrivere in silenzio).

**Fuori-sistema (Crown Oil + supplier — possiamo solo assemblare, non scrivere):**

5. **Pack evidenza F1/F3:** per gli effettivi supplier di pneumatici a fine vita,
   ottenere (a) scope/PoS ISCC che nomina i **punti di raccolta**, (b) autorizzazioni
   tyre-handling. È il make-or-break.
6. **Rispondere onestamente a Deeba Q3/Q4** — nominare i punti di raccolta pneumatici
   reali; confermare la lista completa provider 2025 (pneumatici + plastica), non solo il
   trio plastica.
7. **Confermare scope = solo DEL-CRW-2025-2** con DfT (protegge W8).
8. **Crown Oil riapre con DfT** sulla finestra di re-submission (W5).

---

## 9. Conclusione in una riga

Il nostro **sistema dati è audit-ready e in miglioramento** (PASS internamente, `0047`,
litri fatti, mass balance chiude). L'**audit DfT non è vinto** perché i gap vincolanti —
certificazione ISCC dei punti di raccolta pneumatici e registrazione tyre-handling dei
supplier reali — sono **documenti upstream che non deteniamo e non possiamo generare**.
Verde interno ≠ verde regolatore. La prossima mossa è **raccolta documenti via Crown
Oil**, non altro codice.

---

## 10. Split feedstock e tetto premiabile (DEL-CRW-2025-2)

Aggiunta 2026-06-01. Quantifica quanta produzione è *premiabile* (claimable RTFC) sotto
mass-balance, separando rigorosamente le due cause di esclusione. **Tutti i numeri
verificati contro DB prod il 2026-06-01.**

### 10.1 Principio metodologico (fissato)

Due cause di esclusione dal premio, **mai confuse, mai riclassificando il feedstock**:

- **Gate-1 — eleggibilità ELT:** vale solo se il feedstock è genuinamente **non gomma**
  (plastica/organico). Esclusione di *natura del materiale*.
- **Gate-2 — certificazione:** feedstock = **gomma**, ma fornitore senza ISCC cert valido
  / non registrato tyre. Esclusione di *carta*. Si dice "queste gomme non possono essere
  considerate premiabili" — il feedstock **resta gomma**, il volume è non-awardable per
  documentazione, non per tipo.

Le 4 findings DfT F1/F3 operano su **gate-2**: gomme reali da punti raccolta non-ISCC →
escluse per chain non certificata, **non** rietichettate a plastica.

### 10.2 Split input Gen–Ago 2025 (≈25,08 M kg, 8 fornitori)

| Fornitore | Quota input | Feedstock | Cert / PDF (file su disco) |
|-----------|-------------|-----------|---------------------------|
| EFFICIEN | 26,9% | gomma | US201-...2024 + 2025, **entrambi PDF presenti** ✓ |
| KALTIRE | 23,1% | gomma | US201-...2024 + 2025, **entrambi PDF presenti** ✓ |
| PYRCOM | 15,4% | gomma | ES216-20249051, **PDF presente** ✓ |
| ESENTTIA | 10,0% | plastica | PDF presenti — irrilevante (gate-1, non gomma) |
| LE5TON ≤5t | 9,8% | gomma | 3 placeholder + 1 → **self-decl ISCC accettata** |
| BOLDER | 7,7% | gomma | US201-...2024 + 2025, **entrambi PDF presenti** ✓ |
| BIOWASTE | 4,6% | organico | gate-1 |
| LITOPLAS | 2,4% | plastica | gate-1 |

Gennaio = era plastica/organico (ESENTTIA+BIOWASTE+LITOPLAS) + LE5TON gomma 80.305 kg.
Feb–Ago = pivot ELT; unico non-elig = ESENTTIA (78k–186k kg/mese, 4–6%).

> **Rettifica 2026-06-01 (importante).** Una prima stesura di questo §10 segnalava "6 PDF
> mancanti" e PYRCOM "senza PDF". **Errato.** Quei valori derivavano dalla colonna DB
> `pdf_ref`, non backfillata per 6 certificati. I **file PDF esistono tutti** su disco
> (`/data/certificates/supplier-q3/`), inclusi i rinnovi 2025 e PYRCOM, e sono serviti dal
> frontend. Non c'è alcun gap di evidenza PDF. L'unico difetto in-sistema è la colonna
> `pdf_ref` da allineare ai file già presenti — igiene dati, non documento mancante
> (`feedback_backfill_after_migration`). Lezione: verificare il file, non il proxy-colonna.

### 10.3 Metodo di calcolo

Pro-rata mass-balance (pool pirolisi commingled, nessun litro fisico per-feedstock):

```
elig_pct[mese]      = Σ kg feedstock premiabile / Σ kg totali
eu_premiabile[mese] = eu_prod_litres[mese] × elig_pct[mese]
eu_pct totale       = Σ eu_premiabile / Σ eu_prod_litres
```

Caveat: proxy `codice fornitore = feedstock` (no colonna `feedstock_type`, Sprint α
deferred — W2); ratio kg applicato a litri assume resa uniforme tra feedstock; pro-rata
presuppone DfT accetti claim parziale (non all-or-nothing).

### 10.4 Due scenari di esito (EU / DEV-P100, totale 9.502.019 L)

La sola leva è **gate-2 upstream** (F1/F3): se DfT accetta la filiera gomma (scope ISCC
punti di raccolta + registrazione tyre dei provider). I PDF cert sono tutti presenti →
nessun haircut PDF. Lo scenario "realistico 69,7% PYRCOM-escluso" della prima stesura
**è ritirato**: era basato sul PDF PYRCOM erroneamente ritenuto mancante.

| Scenario | EU premiabile | % | PLUS premiabile | % | Condizione |
|----------|---------------|---|-----------------|---|------------|
| **Atteso** | 8.135.375 L | 85,6% | 9.867.472 L | 83,5% | DfT accetta filiera gomma (cert + PDF a posto) + LE5TON self-decl |
| **Negativo** | ≪ 85,6% | — | — | — | DfT mantiene F1/F3 e contesta la filiera gomma (volume upstream-dipendente) |

Il delta non dipende da carte nostre (in ordine) ma da **documenti upstream** non in nostro
possesso: scope ISCC dei punti di raccolta + registrazione tyre-handling.

### 10.5 EU premiabile mensile (scenario tetto)

| Mese | EU prod L | elig% | EU premiabile L |
|------|-----------|-------|-----------------|
| 2025-01 | 1.006.386 | 2,4 | 23.888 |
| 2025-02 | 1.211.904 | 95,3 | 1.154.532 |
| 2025-03 | 952.290 | 97,3 | 926.489 |
| 2025-04 | 1.118.245 | 96,5 | 1.078.603 |
| 2025-05 | 1.314.457 | 94,0 | 1.236.090 |
| 2025-06 | 1.106.127 | 95,4 | 1.055.665 |
| 2025-07 | 1.479.248 | 96,1 | 1.422.284 |
| 2025-08 | 1.313.363 | 94,2 | 1.237.824 |

Gennaio **non** è 0 premiabile: 23.888 L da LE5TON (gomma, self-decl). Resto Gennaio
(ESENTTIA/BIOWASTE/LITOPLAS) fuori per gate-1 reale, feedstock invariato.

### 10.6 Azioni a più alto valore

1. **Scope ISCC punti di raccolta pneumatici** (upstream, via Crown Oil) → risponde F1.
   Make-or-break.
2. **Registrazione tyre-handling provider** (upstream) → risponde F3.
3. **Documentazione sito** coerente (foto/capacità/date) → risponde F4.
4. **(Interno, minore) Backfill colonna `pdf_ref`** ai file PDF già presenti su disco —
   igiene dati, non evidenza. Annulla il falso positivo W1.

---

_Verificato contro DB prod + repo il 2026-06-01. Nessuna affermazione in questo documento
è non-verificata in-sistema; tutti gli item fuori-sistema sono marcati come tali._
