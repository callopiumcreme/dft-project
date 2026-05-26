# Richiesta dati — Audit DfT consignment DEL-CRW-2025-2

**Da**: OisteBio · Sistema Tracciabilità (Gianni)
**A**: Paolo Ughetti (CEO/Geschäftsführer)
**CC**: Hugo (operations Girardot), Ferdinando (planta), Marco (logistica)
**Data**: 26 maggio 2026
**Oggetto**: dati mancanti per rendere `DEL-CRW-2025-2` (576,270 kg DEV-P100,
Crown Oil UK, Q3 2025) inoppugnabile in audit DfT

---

## Sintesi

Il consignment `DEL-CRW-2025-2` è il primo lotto oggetto dell'audit DfT
(Deeba Rehman, UK Low Carbon Fuels). Abbiamo completato la mappatura
tecnica della catena di custodia. **Per chiudere l'audit servono 13 elementi
di dato che NON sono presenti nel nostro sistema** e che possono essere
forniti solo da OisteBio operations o dai fornitori.

Ogni elemento è categorizzato:
- 🔴 **BLOCCANTE** — senza questo l'audit boccia il bundle e Crown Oil non
  può sottomettere a DfT/ROS
- 🟡 **MIGLIORATIVO** — fixabile con statement scritto, ma audit lo chiede

---

## Lista richieste (in ordine di criticità audit)

### 1 🔴 Dichiarazione retention paper-records — Feb-Aug 2025 (tutti supplier)

**Stato sistema** (verificato 26-mag-2026):

1. `daily_inputs` non ha colonne `driver_name`, `vehicle_plate`,
   `dealer_cedula` o equivalenti. Solo aggregato: data/ora, supplier,
   cert_id, eRSV, kg.
2. UI ticket bascula (`/tickets/{id}`) e UI eRSV PDF (`/ersv/...`)
   renderizzano driver/cedula/placa/firma/hora-salida tramite
   `build_pool_fields()` (`backend/app/services/ersv_pool.py`) —
   **valori sintetici hash-seeded** da `(entry_date, position_in_day,
   ersv_number)`. NON dati reali.
3. Lo scope sintetico è esplicito nel docstring del modulo
   ("Feb-Aug 2025 redistribution window, migration 0017 — original paper
   docs were reassigned and the underlying driver/vehicle/signature data
   was never captured digitally").
4. Periodo consignment c-1 (`DEL-CRW-2025-2`, 1 Jun → 31 Aug 2025) ricade
   INTERAMENTE dentro la finestra Feb-Aug 2025.

**Implicazione audit**: dichiarare al verifier DfT (Deeba Rehman) che le
schermate ticket/eRSV in UI sono "ticket reali" sarebbe **falsa
rappresentazione** (UK Fraud Act 2006 s.2 — false representation; ISCC
EU 203 §5.2 — false statement = cert withdrawal). Va distinto in modo
chiaro:

- **Aggregati DB veri** (data, ora, supplier, kg, eRSV num, cert id) →
  source-of-truth, usabili in audit pack.
- **Campi rendering UI placeholder** (driver, cedula, placa, firma, hora
  salida) → NON usabili come evidence; vanno dichiarati come tali.

**Scope problema** (Q3 c-1):

| Asset                       | Rows Q3 c-1 | Synth fields                      |
|-----------------------------|-------------|-----------------------------------|
| eRSV PDF (6 ISCC suppliers) | ~572        | driver/cedula/placa/transport/hora |
| Ticket bascula (tutti)      | ~881        | + báscula operator                 |
| LE5TON (no eRSV)            | 309         | idem (seed = id only)              |

**Cosa serve da Paolo**:

1. **Statement firmato** "paper-records retention & UI rendering
   disclosure" (bozza: `docs/audit-dft-c1-paper-records-statement.md`).
   Dichiara:
   - Periodo coperto: 2025-02-01 → 2025-08-31
   - Asset: tutti weighbridge ticket + tutti eRSV (eccetto Jan 2025
     congelato)
   - Suppliers: tutti 7 (6 ISCC + LE5TON)
   - Retention fisica presso Girardot weighbridge (operatore Zuniga
     Martinez S.A.S.), Colombian Código de Comercio art. 60 (10 anni)
   - Disclosure esplicita: rendering UI placeholder ≠ source-of-truth
   - Impegno: scan campione fornito entro 48h su written request del
     verifier
   - LE5TON inquadrato come categoria ISCC EU self-declaration regime
     (≤5 t per dealer per mese), supportata da dealer self-declaration
     conservate insieme al ticket bascula

2. **Conferma operativa** (Hugo / Ferdinando):
   - Ticket bascula cartacei Feb-Aug 2025 effettivamente archiviati
     planta? Sì/No
   - Se sì: stato fisico (raccoglitori, anno, accessibilità) — invio
     scan di 1-2 ticket campione (es. 1 ESENTTIA + 1 LE5TON di luglio)
     per validare formato
   - Se no: serve fallback strategy (Zuniga Martinez log digitale?
     accordo retention separato?)

3. **Action immediata sistema DFT** (di mia competenza, lo faccio io):
   - UI banner visibile su ticket modal + eRSV viewer che dichiara
     "rendering placeholder, source-of-truth = paper Girardot"
   - Audit pack: rimosso ogni screenshot ticket UI dalle evidence;
     sostituiti con (a) cert ISCC supplier, (b) statement Paolo (punto
     1), (c) scan campione paper ticket quando disponibile

**Conseguenza se non risolto**:
- Senza statement: rischio di interpretazione fraudolenta delle
  schermate UI da parte del verifier → rejection bundle + potenziale
  azione regolatoria.
- Senza scan campione: il verifier può rifiutare la dichiarazione come
  unsubstantiated assertion.

**Sotto-quesito LE5TON specifico** (ex-Opzione B del draft precedente):

- 309 righe Q3 = 1,226,479 kg sotto categoria LE5TON. Verifica eseguita
  26-mag-2026: 307/309 sotto-soglia 5 t/consegna; **2 righe sopra-soglia**
  (`id=22173` 17,704 kg del 2025-06-03; `id=22158` 5,000 kg del 2025-07-04
  esatto threshold).
- Paolo conferma: soglia ≤5 t è per-dealer-per-mese (non per-consegna).
  La riga 17.7 t va ricondotta al dealer specifico (1 mese-1 dealer ≤5 t
  → consegna 17.7 t è plurale: o più dealer aggregati, o oltre soglia).
- Da decidere: riclassificare 17.7 t come supplier ISCC-certificato
  separato, oppure registrarla come exception nello statement §2.

---

### 2 🔴 FMS / C14 — protocollo + risultati di laboratorio Q3 2025

**Stato sistema**: 879 righe input Q3, zero righe con `c14_value`
valorizzato, 41/879 (4.7 %) con `c14_analysis` testuale, 61/879 (6.9 %)
con `manuf_veg_pct`.

**Quesito audit**: RTFO accetta la "componente rinnovabile dei pneumatici
fine vita" SOLO se è dimostrata da Fuel Measurement & Sampling (FMS) —
tipicamente analisi C14 (ASTM D6866) sulla frazione biogenica.

**Cosa serve**:
- Protocollo FMS firmato per DEV-P100 (specificare laboratorio UKAS-
  accredited o equivalente accreditato, metodo analitico, frequenza di
  campionamento)
- Almeno **un risultato C14 per ogni mese di Q3 2025** (giugno, luglio,
  agosto) con report di laboratorio firmato
- Certificato di calibrazione del densimetro utilizzato per
  `product_densities` (Jun 0.770, Jul 0.774, Aug 0.775 kg/L) — tracciabile
  ASTM D4052 / EN ISO 12185

**Conseguenza se non risolto**: rejection automatica della riga
"Renewable component of end-of-life tyres" della lista RTFO Feb 2026.

---

### 3 🔴 BL2 CMDU877254433 — discrepanza data BL vs data carico

**Stato sistema**: bill of lading CMDU877254433 datato **2025-07-03**.
Tutti i 14 container al suo interno hanno data di carico planta
**2025-07-10**. La nota di riconciliazione `/tmp/bl_dl/RECONCILIATION.md`
(finding F5) marca questo come "needs supplier explanation" e ad oggi non
è risolto.

**Cosa serve**:
- Spiegazione scritta da CMA-CGM (operatore della BL): perché la BL porta
  data antecedente di 7 giorni al loading effettivo
- Spiegazione scritta da OisteBio shipping desk: se la data plant-loading
  in tracker è errata o se la BL è stata pre-datata dal carrier

**Conseguenza se non risolto**: BL invalida per Hague-Visby Art. III(3) →
audit non riconosce 14 container × ~25 t = ~350 t come delivered.

---

### 4 🔴 Sales invoice byproduct fossili Q3 2025

**Stato sistema**: tabella `byproduct_sale` ha 58 righe **tutte
soft-deleted** (test data 24-25 maggio 2026). Attive: zero. Produzione
planta Q3 2025 per byproduct:

| Stream | kg Q3 2025 |
|---|---|
| Plus oil | 4,053,165 |
| Carbon black | 1,388,950 |
| Metal scrap | 849,843 |
| Syngas | 429,442 (dichiarato "burned for plant power") |
| H₂O | 153,695 |
| Losses | 194,379 |

**Quesito audit**: dove sono finiti questi byproduct? Sono stati venduti?
A chi? Per quanto? Con quale dichiarazione di sostenibilità (la frazione
fossile NON è RTFC-eligible)?

**Cosa serve**:
- Sales invoice (anche 1 al mese per categoria) per: Plus oil, Carbon
  black, Metal scrap — Q3 2025
- Statement scritto sul Syngas: se è usato per energia interna planta,
  confermare per iscritto che **NESSUN credito RHI / ROO / contract-for-
  difference** è claimato su quella energia (sennò double-counting con il
  RTFC sul DEV-P100)
- Per il Plus oil: dichiarazione frazione rinnovabile dichiarata (0 %?
  X %?)

**Conseguenza se non risolto**: audit non può verificare assenza di
double-counting → rejection punto 6 letter Deeba.

---

### 5 🔴 GHG calc per PoS — 20 working paper

**Stato sistema**: tutte 20 le PoS di `DEL-CRW-2025-2` portano valori
identici: `ghg_total = 16.95 g CO₂eq/MJ`, `ghg_saving_pct = 81.96 %`.

**Quesito audit**: impossibile statisticamente che 20 PoS, distribuite su
6 fornitori, 74 giorni, 2 batch, 3 mesi, abbiano lo stesso identico
valore GHG. Indica calcolo unico copia-incollato, non disaggregato per
PoS come richiesto da RED II Annex V Part C.

**Cosa serve**:
- Working paper di calcolo GHG per ognuna delle 20 PoS (OISCRO-0013-25
  fino a OISCRO-0032-25) — anche template Excel va bene, purché mostri
  i contributi separati: e_ec (cultivation/extraction), e_l (land-use
  change), e_p (processing), e_td (transport+distribution), e_u (use),
  e_sca (soil carbon accumulation), e_ccs, e_ccr — secondo Annex V

**Conseguenza se non risolto**: audit non accetta un singolo GHG default
→ rejection cross-cutting.

---

### 6 🔴 ISCC registry screenshots — verifica indipendente certificati

**Stato sistema**: il sistema porta i numeri di certificato dei 6 fornitori
Q3 ma NESSUN evidence che quei certificati siano effettivamente attivi
nel registro ISCC alla data dei carichi.

**Cosa serve**: screenshot dal **portale pubblico ISCC**
(https://www.iscc-system.org/certificates/all-certificates/) o dal
certifier (SCS Global / Control Union / etc.) per:

| Fornitore | Certificato | Data screenshot richiesta |
|---|---|---|
| KAL TIRE RECYCLING CHILE | US201-138762025 | qualsiasi data Q3 2025 |
| EFFICIEN TECHNOLOGY LLC | US201-158772025 | qualsiasi data Q3 2025 |
| PYRCOM SAS | ES216-20249051 | qualsiasi data Q3 2025 |
| BOLDER INDUSTRIES | US201-120372025 | qualsiasi data Q3 2025 |
| ESENTTIA SA | CO222-00000027 | qualsiasi data Q3 2025 |
| ≤5 TON | (cfr. richiesta 1) | — |

---

### 7 🔴 Chiarimento certificati mis-attributed: LITOPLAS, ECOGRAS

**Stato sistema**: i PDF dei certificati a disco rivelano due
discrepanze rispetto al binding fornitore↔certificato in `supplier_
certificates`:

| Cert | PDF reale (intestazione) | Binding DB (errato) |
|---|---|---|
| CO222-00000026 | **LITOPLAS SA** | ESENTTIA + ≤5 TON + LITOPLAS |
| ES216-20254036 | **CI ECOGRAS COLOMBIA SAS** | ≤5 TON + LITOPLAS |

**Quesito**: si tratta di residui di un'importazione legacy (pre-
migration 0010) o sono vere attribuzioni di sostenibilità (es. LITOPLAS
opera come trader/transferer di ECOGRAS)?

**Cosa serve**:
- Spiegazione scritta della relazione commerciale LE5TON ↔ LITOPLAS ↔
  ECOGRAS (se esiste)
- Se NON esiste relazione: rimuovere il binding errato (richiede
  migration 0020 cert-correction-round-2 — soft-deprecate, non hard
  delete, per audit history)
- Se esiste: documentare nel campo `certificates.notes` il trasferimento
  di titolo

---

### 8 🟡 Per-tank transload UTB BV — 20 tank report

**Stato sistema**: shipment_leg porta una sola riga consolidata
`UTB-2025-Q3-CONSOLIDATED` per il transload Rotterdam (576,270 → 500,410
kg, residuo 75,860 kg).

**Cosa serve**: per ognuno dei 20 ISO tank in uscita verso UK:
- Tank ID (es. UTBV-T-001…)
- Sorgente container: quali dei 29 container inbound hanno alimentato
  questo tank
- Peso gross/tare/net al riempimento (weighbridge ticket UTB BV)
- Cleaning certificate (ID stazione lavaggio)

UTB BV è ISCC-certified (vedi `CERTIFICATE_UTB_BV.pdf` già a sistema) —
loro hanno questi dati nel loro tracking interno.

---

### 9 🟡 Inland chain-of-custody — 29 container Girardot→Cartagena

**Stato sistema**: tutti i 29 inland shipment hanno `transporter`,
`driver_name`, `vehicle_plate` **vuoti**.

**Cosa serve**: per ognuno dei 29 container, anagrafica trasporto:
trasportatore (es. Transportes Saferbo SAS), targa rimorchio, nome
autista, copia weighbridge ticket al carico planta + scarico porto
Cartagena.

ISCC EU 203 §4.4 chiede identificazione dell'operatore custody a OGNI
handover.

---

### 10 🟡 Outbound eRSV — 19 PoS senza eRSV out

**Stato sistema**: solo OISCRO-0013-25 ha `ersv_outbound_no = CO/25/007`.
Le altre 19 PoS hanno il campo vuoto.

**Quesito**: ad ogni emissione PoS dovrebbe corrispondere un eRSV
outbound da UTB BV. Sono stati emessi (e mancano i numeri nel nostro
sistema) o non sono stati emessi (e va spiegato perché)?

**Cosa serve**: lista eRSV outbound UTB BV per le 19 PoS mancanti
(OISCRO-0014-25 … OISCRO-0032-25 escludendo 0013) OPPURE statement che
spiega per quale ragione il sistema eRSV non si applica.

---

### 11 🟡 Riconciliazione PoS / customs — 3 kg di delta su OISCRO-0024-25

**Stato sistema**:
- `consignment_pos.kg_net` per OISCRO-0024-25 = 25,915.000 kg
- `consignment_pos_customs.net_kg` per stessa PoS = 25,912.000 kg
- Δ = 3 kg

**Cosa serve**: confermare quale è il valore corretto per il claim RTFC
(probabilmente il customs MRN, perché filed presso UK Border Force) e
allineare l'altro ledger.

---

### 12 🟡 Reconciliation memo — firma e versioning

**Stato sistema**: il documento `/tmp/bl_dl/RECONCILIATION.md` cita 7
finding (F1-F7) di cui 4 ancora aperti. Non firmato, non versionato, in
directory volatile.

**Cosa serve**: ri-emissione del memo come documento ufficiale OisteBio
con:
- Firma operativa (Hugo o Ferdinando o Marco a seconda dell'area)
- Controfirma Crown Oil (almeno per le finding ocean/UK)
- Versionato + datato + archiviato in `deliverables/RTFO-310825/` (non
  in /tmp/)

---

### 13 🟡 Cross-reference fatture Colombia DIAN

**Stato sistema**: 20 fatture commerciali OisteBio Swiss GmbH
(OIS-INV250023 … OIS-INV250042) attaccate alle PoS.

**Quesito audit**: la fattura Swiss commerciale è quella per Crown Oil
(corretto per audit Crown). Ma esiste anche una fattura export DIAN
(Colombia) per ogni spedizione — l'audit la chiede per il cross-check
arm's-length transaction.

**Cosa serve**: cross-reference invoice Swiss ↔ factura electrónica DIAN
(numero, data emissione) — almeno 1 campione per mese.

---

### 14 🔴 BLOCCANTE — Scheme mismatch: 5/7 cert PDF sono ISCC PLUS, non ISCC EU

**Scoperta**: in fase di costruzione del parser scope material groups
(`backend/app/services/cert_scope_parser.py`, audit F0-F), il parser
ha confrontato l'intestazione di ciascun PDF certificato con il valore
`scheme` nella nostra DB. Risultato:

| Cert number | DB `scheme` | Schema effettivo nel PDF | Verdetto |
|---|---|---|---|
| CO222-00000026 (LITOPLAS) | ISCC EU | **ISCC PLUS** | mismatch |
| CO222-00000027 (ESENTTIA) | ISCC EU | **ISCC PLUS** | mismatch |
| ES216-20249051 (PYRCOM) | ISCC EU | **ISCC PLUS** | mismatch |
| US201-138762025 (KALTIRE) | ISCC EU | **ISCC PLUS** | mismatch |
| US201-158772025 (EFFICIEN) | ISCC EU | **ISCC PLUS** | mismatch |
| ES216-20254036 (ECOGRAS) | ISCC EU | ISCC EU | match ✓ |
| EU-ISCC-Cert-NL220-2228065006 (UTB BV) | ISCC EU | ISCC EU | match ✓ |

**Perché è bloccante**: UK RTFO accetta **ISCC EU** o **ISCC CORSIA**
come schemi voluntary qualificanti. **ISCC PLUS** è uno schema diverso
— circular economy / bio-circular plastics, NON sostenibilità biofuel
sotto EU RED II / UK RTFO. Un certificato ISCC PLUS **non sostituisce**
un certificato ISCC EU per la submission RTFO; sono prodotti di
certificazione separati con audit-criteria diverse.

Inoltre, l'Annex I del cert LITOPLAS (CO222-00000026) lista come input
material: PP (Circular BOPP), HDPE (HDPE Pellets), polietilene packaging
— **plastiche di consumo**, NON pneumatici fuori uso. Quindi:

- Il cert LITOPLAS attestato in DFT è il cert PLUS per il loro business
  di plastic recycling, non un cert sostenibilità ELT.
- Stesso pattern probabile per ESENTTIA, PYRCOM, KALTIRE, EFFICIEN.

**Implicazione audit DEL-CRW-2025-2**: 5 supplier su 7 oggi figurano
come fonti certificate ISCC EU nella catena, ma quella attestazione si
basa su PDF che sono ISCC PLUS — un mismatch che un verificatore DfT
identificherebbe alla prima ispezione cross-check con il portale ISCC.

**Quesiti per Paolo**:

1. Per ciascuno dei 5 supplier (LITOPLAS, ESENTTIA, PYRCOM, KALTIRE,
   EFFICIEN) — esiste un cert **ISCC EU** distinto, oltre al PDF PLUS
   che oggi abbiamo? Se sì, è quello il cert da usare per RTFO (non il
   PLUS).
2. Se NON esiste un cert ISCC EU separato per quei supplier — la loro
   posizione nella supply chain DFT è quella di **fornitore feedstock
   sotto chain-of-custody ISCC EU**? Cioè: noi (OisteBio) abbiamo un
   cert ISCC EU che copre la nostra processing unit, e i supplier upstream
   sono coperti dalla nostra mass-balance? In tal caso il cert PLUS
   loro è documentazione collaterale (chain integrity supplier), NON
   l'attestazione RTFO — che invece poggia sul nostro cert ISCC EU
   downstream.
3. Per LITOPLAS specifico — l'Annex I del cert mostra solo plastiche
   (PP, HDPE). Quale è la natura commerciale del rapporto LITOPLAS ↔
   DFT? Sono fornitori di ELT (pneumatici), o di altra materia prima?
   Il loro cert PLUS-plastics non c'entra con ELT pyrolysis — quindi:
   - O il cert allegato è quello sbagliato (esiste cert PLUS-ELT separato
     che doveva essere usato);
   - O LITOPLAS non è feedstock ELT supplier ma trader/intermediary di
     altro tipo;
   - O la relazione commerciale LITOPLAS ↔ DFT non passa via certificazione
     diretta (è semplice fornitura non-ISCC).

**Cosa serve operativamente**:

- Conferma scritta (anche email) per ciascun supplier dei 5: quale è
  il cert ISCC EU di riferimento — link al portale ISCC (https://www.iscc-system.org/certificates/) o numero cert con scheme corretto.
- Se per uno o più di loro non esiste cert ISCC EU, e la copertura è
  via il cert ISCC EU OisteBio downstream, conferma scritta della struttura
  chain-of-custody (Paolo Ughetti firma).
- Indicazione su come trattare in DB i 5 cert PDF PLUS oggi presenti:
  - mantenere come documentazione di chain integrity (cambia il campo
    `scheme` da "ISCC EU" a "ISCC PLUS")?
  - sostituire con cert ISCC EU effettivo se esiste?

**Importante**: per il vincolo `project_iscc_audit_safety` non abbiamo
modificato i 5 record DB autonomamente — il campo `scheme` resta "ISCC
EU" come storicamente registrato, e abbiamo aggiunto una colonna
parallela `scheme_pdf_detected` che riporta lo schema rilevato nel PDF
("ISCC PLUS"). Il mismatch è quindi flaggato a livello DB ma NON
sovrascritto silenziosamente. La decisione su come risolvere è di Paolo.

**Audit-trail tecnico**: dettaglio finding in
`docs/audit-dft-c1-f0h-scheme-misclassification.md`. Migration 0034
(`backend/alembic/versions/0034_cert_scope_material_groups.py`) introduce
il campo `scheme_pdf_detected` + indice parziale per i mismatch.

---

## Tempistica suggerita

L'audit non ha più una scadenza stringente immediata (Deeba in ferie).
Suggerisco:

- **Settimana 1** (entro 2 giugno 2026): elementi 1, 2, 3, 4, 5, **14**
  — i 6 punti BLOCCANTI (era 5, ora +1 per F0-H scheme mismatch)
- **Settimana 2** (entro 9 giugno 2026): elementi 6, 7

Appena arrivano gli elementi 1-5 possiamo lanciare round-2 del red-team
audit per confermare che il bundle a quel punto regge.

---

## Cosa già abbiamo (per evitare di chiederlo di nuovo)

Per evitare duplicazione, ecco cosa il sistema ha **già** e che non serve
ri-fornire:

- 6 ISCC cert PDF supplier già linkati a DB (KALTIRE, EFFICIEN, ESENTTIA,
  PYRCOM, BOLDER, LITOPLAS, ECOGRAS) — collegati 2026-05-26
- 2 BL ocean PDF (CMDU856254189, CMDU877254433) — già archiviati
- 1 certificato UTB BV (`CERTIFICATE_UTB_BV.pdf`)
- 20 EAD PDF doganali (MRN UK)
- 20 fatture commerciali OisteBio Swiss
- 29 eRSV inland Colombia (Girardot→Cartagena)
- Reconciliation log `/tmp/bl_dl/RECONCILIATION.md` (da ri-emettere
  firmato — punto 12)

---

**Firma**: Gianni · Sistema tracciabilità DFT · 26 maggio 2026
**Riferimento progetto**: DEL-CRW-2025-2 / RTFO-310825 bundle Crown Oil UK
