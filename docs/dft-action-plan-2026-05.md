# Piano d'azione DfT — RTFC 2025

**Oggetto:** Applicazione RTFC 2025 Crown Oil — development diesel da pneumatici a fine vita (Colombia / OisteBio).
**Scope:** **Solo Gennaio 2025** — bundle singolo RTFO-310125. Altri bundle 2025 (Feb/Mar/Jul/Ago) fuori scope corrente; trattenuti per applicazioni 2026 forward o submission successive.
**Contesto:** Lettera formale rigetto DfT ricevuta 9 marzo 2026 a seguito meeting del 5 marzo 2026. Bundle RTFO-310125, RTFO-280225, RTFO-310325, RTFO-310725, RTFO-210825 programmati cancellazione 13 marzo 2026. Deadline originale resubmission ROS: 14 maggio 2026.
**Data piano:** 13 maggio 2026.
**Owner piano:** Crown Oil (applicant) con OisteBio (produttore) e team digital ingest a supporto.
**Stato documento:** piano operativo, versione 1. Aggiornamenti via commit git man mano che il piano evolve.

---

## 1. Sintesi esecutiva

DfT ha rigettato l'intera pathway 2025 citando tre categorie di carenze: (a) chain of custody ISCC inadeguata, (b) evidence feedstock incompleta e mancanza production log di conversione, (c) submission inconsistenti e incrementali. L'Unit ha però lasciato esplicitamente una porta aperta: una resubmission coerente può essere depositata su ROS entro 14 maggio 2026, con verifica permessa dopo tale data previo consenso Unit.

Sono trascorsi due mesi dal rigetto senza comunicazione formale all'Unit. Il periodo è stato usato per ingaggiare specialista digital ingest e audit e ricostruire la base evidenziale a partire dati primari. Lavoro sufficientemente avanzato per:

- presentare mass-balance pienamente riconciliato per **Gennaio 2025** a standard audit;
- proporre finestra di rimedio compressa con milestone delivery e checkpoint intermedio;
- impegnarsi a submission unica e coerente per Gennaio 2025 senza evidence incrementale o retrospettiva.

**Scope ridotto deliberato.** Submission concentrata su singolo mese (Gennaio 2025) per massimizzare qualità evidenziale e probabilità accettazione. Bundle Feb/Mar/Jul/Ago 2025 esclusi dalla resubmission corrente: trattenuti per submission separate dopo accettazione del bundle Gennaio, o consolidati in applicazione 2026.

Il piano definisce gli step di esecuzione della strategia di resubmission. Si articola su due binari: richiesta estensione immediata (Track A) e, in parallelo, programma strutturato di rimedio (Track B) che procede indipendentemente dall'esito dell'estensione e posiziona la pathway per il 2026 in avanti.

---

## 2. Riconoscimento findings DfT

Non contestiamo il rigetto. Per ciascuna carenza citata riconosciamo la sostanza e identifichiamo il rimedio:

| Finding DfT | Riconosciuto | Track di rimedio |
|---|---|---|
| Chain of custody ISCC non dimostrata | Sì | PoS retroattivo da ciascun vero collecting point, legato a batch di input specifici nel sistema digital ingest. |
| Fuel non coperto da certificati ISCC / PoS validi | Sì | Cross-reference daily inputs contro periodi validità certificati ISCC; flag e rimedio gap prima della submission. |
| Record feedstock incompleti o inconsistenti | Sì | Report mass-balance generati da database primario con closure giornaliera a zero, esportati come PDF immutabile con hash crittografico. |
| Production log conversione (kg → litri) non forniti | Sì | Aggiungere colonna `litres` alla tabella production; backfill da record produzione OisteBio; esporre nell'export mass-balance. |
| Maggior parte feedstock provider non registrati per gestione pneumatici | Sì | Ottenere autorizzazioni regolatorie Colombia (ANLA / Ministerio de Ambiente) per ciascun vero collecting point, con legalizzazione consolare e traduzione giurata EN. |
| Submission incrementale | Sì | Bundle Gennaio 2025 — body unico coerente entro deadline estensione. Nessun upload parziale. |
| Inconsistenze su immagini sito produzione, capacità, date inizio | Sì | Pack documentazione sito consolidato da fonte autoritativa; una versione firmata per item. |
| Evidence retrospettiva | Sì | Ogni documento sottomesso pre-datato finestra resubmission e fonte indipendente. |

---

## 3. Strategia a due binari

### Track A — Richiesta estensione (immediato, basso costo, esito opzionale)

Sottomettere richiesta formale estensione a DfT LCF Delivery Unit il 13 maggio 2026 chiedendo che la deadline ROS del 14 maggio 2026 sia estesa al **13 giugno 2026** (estensione di 30 giorni) per submission del solo bundle **RTFO-310125 (Gennaio 2025)**, con checkpoint status intermedio al **30 maggio 2026**.

Richiesta estensione preceduta da telefonata di cortesia al contact DfT nominato la mattina del 13 maggio 2026 per segnalare intent prima dell'arrivo della submission scritta.

La richiesta è accompagnata da un body iniziale di evidence (Annex A–E, vedi §6) che dimostra lo standard a cui sarà preparata la resubmission.

**Scope limitato come segnale di disciplina.** Submission del solo Gennaio 2025 riduce richiesta a DfT e dimostra disciplina di submission coerente — risposta diretta alla critica "incremental and inconsistent submission". Crown Oil indica che ulteriori bundle 2025 saranno considerati separatamente solo dopo accettazione del primo.

Probabilità successo incerta. I due mesi di silenzio e i precedenti motivi rigetto pesano contro; l'evidence sostanziale già preparata, lo scope limitato della richiesta (1 mese, 30 giorni) e l'evidenza di scope-discipline pesano a favore. La richiesta è inviata comunque perché il costo è una giornata e l'upside è il recupero del bundle Gennaio 2025 più il posizionamento per bundle successivi.

### Track B — Rimedio strutturato (indipendente esito Track A)

Indipendentemente dal fatto che DfT conceda o meno l'estensione, il lavoro di rimedio procede. Scope corrente Track B:

- bonifica fornitori limitata ai **lotti Gennaio 2025** (PoS retroattivo, mapping collecting point corretto);
- evidence pack consolidato per bundle Gennaio 2025;
- infrastruttura DFT (audit log, export crittografico, schema `collection_points`, schema `litres`) — riutilizzabile per bundle successivi e applicazioni 2026.

I deliverable prodotti dal Track B sono:

- funzionalmente necessari per la resubmission Gennaio 2025 (Track A);
- riutilizzabili per submission bundle Feb-Ago 2025 a finestra successiva o per applicazioni 2026 forward;
- utilizzabili come evidence fondazionale se Crown Oil e OisteBio decidono di ingaggiare un verifier ISCC indipendente (Bureau Veritas, SGS, DNV) per applicazioni forward.

Track B è il lavoro che crea valore duraturo. Track A è il tentativo di recuperare il bundle Gennaio 2025.

---

## 4. Timeline

Tutte le date orario UK.

### Day 0 — 2026-05-13 (oggi)

| Orario | Azione | Owner |
|---|---|---|
| Mattina | Telefonata Crown Oil → contact DfT LCF Unit nominato, segnalare intent | Crown Oil |
| Mattina-Pomeriggio | Generare Annex A–E dal sistema digital ingest DFT | Team ingest |
| Pomeriggio | Iniziare bonifica fornitori (sostituire entità mal classificate) | OisteBio + team ingest |
| EOD | Email formale richiesta estensione con allegati, cc compliance lead OisteBio | Crown Oil |

### Day 1 — 2026-05-14 (deadline originale DfT)

- **Nessuna submission su ROS.** Sottomettere bundle incompleti = rigetto sugli stessi motivi della prima investigazione.
- Continuare lavoro bonifica fornitori.
- Attendere risposta DfT.

### Day 2-4 — 2026-05-15 → 2026-05-17 (finestra risposta)

- Confermare risposta scritta da DfT.
- Se estensione concessa: procedere Track B con deadline vincolante 30 giugno 2026.
- Se estensione rifiutata: continuare Track B, ri-targettare applicazioni 2026 forward.

### Settimana 1 — 2026-05-19 → 2026-05-25

- Contattare compliance lead Litoplas, Biowaste, Esenttia.
- Richiesta scritta formale di PoS ISCC retroattivo **per gennaio 2025** (solo lotti Jan).
- Confermare certifier ISCC incaricato (Bureau Veritas Colombia / SGS Colombia / altro) e ingaggiare timeline.
- Identificare e documentare feedstock provider mal classificati nei record gennaio 2025 (vedi §5).
- Sistema DFT: implementare tabella `collection_points`; implementare colonna `litres` nello schema production.
- Compilare evidenza stock carry-over end-Jan: 339.865 kg inventario fisico (Annex D).

### Settimana 2 — 2026-05-26 → 2026-06-01 (include checkpoint intermedio)

- Ricevere bozza PoS retroattivo Gennaio 2025 o follow-up su richieste in sospeso.
- Avviare richieste documenti ANLA / Ministerio de Ambiente per ciascun collecting point (Litoplas/Biowaste/Esenttia).
- Sistema DFT: implementare campo `feedstock_provider_registration` nello schema supplier.
- Sistema DFT: implementare endpoint export PDF mass-balance audit-grade con hash crittografico.
- Sistema DFT: implementare generazione production log end-to-end (kg input → kg processed → litri output) per Gennaio 2025.
- Riconciliazione eRSV gennaio 2025 (verifica duplicati/collisioni mese singolo).
- **Sottomettere status report intermedio scritto a DfT il 30 maggio 2026** (vedi §7 template).

### Settimana 3 — 2026-06-02 → 2026-06-08

- Legalizzazione consolare documenti Colombia (consolato UK, Bogotá) — solo documenti gennaio 2025.
- Traduzioni giurate EN.
- Se ingaggiato: kick-off pre-audit certifier ISCC indipendente — scope Gennaio 2025.
- Assemblare pacchetto finale di submission per bundle RTFO-310125 (vedi §8 struttura).
- Generare snapshot crittografico dello stato database per garantire audit trail evidence Gennaio 2025.

### Day 30-of-window — 2026-06-13

- Audit interno finale del bundle Gennaio 2025 assemblato.
- Cross-reference: ogni chilogrammo gennaio in mass-balance ↔ PoS ISCC ↔ registrazione provider.
- Formattazione finale per requisiti ROS.
- **Submission su ROS.** Bundle singolo RTFO-310125 (Gennaio 2025) — body unico coerente.
- Notificare via email contact DfT nominato della submission.

### Post-submission — 2026-06-14 → 2026-08

- Rispondere prontamente alle domande di verifica DfT su bundle Gennaio 2025. Mai incrementalmente.
- Se approvato bundle Gennaio: avviare assemblaggio bundle successivi (Feb/Mar/Jul/Ago) con stesso standard, finestra da concordare con Unit.
- Se rifiutato: pathway chiusa per bundle 2025; deliverable Track B trattenuti per applicazioni 2026 forward.

---

## 5. Bonifica fornitori e collecting point

L'attuale sistema digital ingest riflette sette record supplier: ESENTTIA, SANIMAX, LITOPLAS, CIECOGRAS, BIOWASTE, ECODIESEL (dormant) e bucket aggregato "≤5 TON" per piccoli batch ISCC autodichiarati. La comprensione working di DfT identifica solo Litoplas, Biowaste ed Esenttia come collecting point.

**Scope corrente: solo lotti Gennaio 2025.** La bonifica fornitori viene applicata in via prioritaria ai daily input gennaio 2025. Riclassificazione dei record storici altri mesi (Feb-Dic 2025) deferita; record corrente preservato in audit trail per applicabilità retroattiva quando i bundle successivi verranno preparati.

Una riclassificazione chirurgica viene eseguita oggi per allineare i record supplier alla vera struttura collecting-point. Princìpi:

- **Nessun hard delete.** Supplier riclassificati = soft-delete con note esplicative riferimento investigazione DfT. Audit trail preservato.
- **Nessuna riscrittura silente.** Ogni riattribuzione di un daily input da fornitore sbagliato al collecting point corretto è loggata in `audit_log` con `old_values` e `new_values`.
- **Volumi preservati.** Totali chilogrammo per data restano invariati. Cambia solo l'attribuzione al collecting point corretto.
- **Certificati preservati.** Record originali certificato ISCC trattenuti anche se riassegnati; provenance del record storico auditabile.
- **Provenance ricostruibile.** Da qualsiasi stato corrente, l'audit log permette ricostruzione dello stato immediatamente precedente la bonifica.

La migration è registrata come `0005_supplier_rectification.py` (o SQL operativo equivalente) e applicata localmente e sul server produzione con verifica closure mass-balance prima e dopo.

L'output di questa bonifica alimenta direttamente Annex B (diagramma supply chain) e Annex C (evidence register).

---

## 6. Body iniziale di evidence (allegati richiesta estensione)

### Annex A — Mass-balance riconciliato Gennaio 2025

Mass-balance giornaliero per **gennaio 2025** generato dal sistema digital ingest OisteBio. Closure giornaliera (input − production − by-products − stock movement) ricostruita su tutti i 31 giorni. Include dettaglio per-giorno, aggregato mensile, e dichiarazione esplicita stock end-Jan 339.865 kg (vedi Annex D). Formato: PDF, firmato, con hash SHA-256 per verifica integrità. **Questo è il bundle target della resubmission corrente** (RTFO-310125).

### Annex B — Diagramma supply chain

Diagramma che mostra quattro layer: origin point (dove applicabile), collecting point (certificati ISCC, post-bonifica), facility OisteBio (ricezione e conversione) e Crown Oil (end supplier UK). Include il PoS ISCC emesso a ogni passaggio.

### Annex C — Evidence register

Tabella di lavoro che elenca ogni documento richiesto per la resubmission **gennaio 2025**, con stato corrente (disponibile, in progress, da raccogliere), owner e data target completamento. Item già disponibili: mass-balance digitale gennaio 2025, audit log, spiegazione stock carry-over. Item da raccogliere: PoS ISCC retroattivo gennaio 2025 da ciascun collecting point, autorizzazioni regolatorie Colombia per i tre collecting point.

### Annex D — Spiegazione stock carry-over end-Gennaio 2025 (MANDATORIO)

Spiegazione scritta dello stock di chiusura end-Gennaio 2025 = **339.865 kg** di feedstock fisico trattenuto in inventario. Composto da 17 K-only rows nel foglio JANUARY2025 (righe 48, 78, 94, 108, 138, 194, 223, 228-233, 267, 283, 314, 330) che rappresentano stock movement / produzione CROWN008 da inventario anno precedente. Documento chiarisce che lo stock end-Jan **non rappresenta perdita né underdeclared input**, è fisicamente disponibile in facility OisteBio e tracciabile via record interno aziendale. Senza il bundle Febbraio nello scope corrente, Annex D è essenziale per spiegare la closure apparente −10.05% di Gennaio.

### Annex E — Piano milestone

Questo documento, sintetizzato in forma tabellare per il pacchetto richiesta estensione.

---

## 7. Checkpoint intermedio — 30 maggio 2026 (template)

```
Subject: RTFO 2025 EoL Tyres Pathway — Interim Status Report (Jan 2025 bundle, per extension agreement)

Dear [Name],

Per the agreement of [DATE], please find Crown Oil's interim status report
against the Evidence Register submitted on 13 May 2026 for the
RTFO-310125 (January 2025) bundle.

Items completed since 13 May:
- [each item from Annex C marked complete, with reference]

Items in progress:
- [each item, with revised completion target if any has slipped]

Items not yet started:
- [each item, with reason and target start]

Risks and dependencies:
- [legalisation timelines, certifier availability, third-party responsiveness]

Confirmation: we remain on track for submission of the RTFO-310125 (January 2025) bundle by 13 June 2026.

[Signed, Crown Oil]
```

(Template in inglese — destinatario DfT UK.)

---

## 8. Struttura pacchetto submission finale — 13 giugno 2026

Bundle singolo RTFO-310125 (Gennaio 2025):

```
bundle_RTFO-310125/
├── 00_cover_letter.pdf                 (Crown Oil firmato, scope Jan 2025)
├── 01_supply_chain_diagram.pdf         (origin → collecting point → OisteBio → Crown Oil)
├── 02_mass_balance_january_2025.pdf    (export sistema DFT, giornaliero + aggregato mensile + closing stock)
├── 03_iscc_pos_chain/
│   ├── litoplas_pos_2025-01.pdf
│   ├── biowaste_pos_2025-01.pdf
│   ├── esenttia_pos_2025-01.pdf
│   └── oistebio_pos_to_crownoil_2025-01.pdf
├── 04_feedstock_provider_authorisations/
│   ├── litoplas_anla_permit.pdf        (legalizzato + traduzione EN)
│   ├── biowaste_anla_permit.pdf
│   └── esenttia_anla_permit.pdf
├── 05_production_conversion_logs_january_2025.pdf   (kg → litri, giornaliero, firmato)
├── 06_audit_trail_export_january_2025.csv           (da tabella DFT audit_log)
├── 07_stock_carryover_explanation.pdf  (Annex D — end-Jan 339.865 kg)
├── 08_independent_audit_letter.pdf     (se certifier ISCC ingaggiato)
└── 09_evidence_index.pdf               (cross-reference docs ↔ punti rigetto DfT)
```

Submission singola su ROS, accompagnata da cover letter Crown Oil che dichiara esplicitamente: (a) scope Gennaio 2025, (b) bundle successivi 2025 considerati separatamente solo dopo accettazione.

---

## 9. Commitment all'Unit

Subordinato alla concessione dell'estensione, Crown Oil e OisteBio si impegnano a:

- **Nessuna ulteriore submission incrementale.** Submission del 13 giugno 2026 sarà body unico coerente per il bundle Gennaio 2025. Bundle successivi 2025 saranno trattati separatamente solo dopo decisione su Gennaio.
- **Scope disciplinato.** Submission corrente limitata a singolo mese — risposta diretta a critica DfT su submission frammentata.
- **Nessuna evidence retrospettiva.** Ogni evidence sarà pre-datata finestra di assemblaggio e fonte indipendente.
- **Trasparenza intermedia.** Status report scritto fornito al 30 maggio 2026.
- **Verifica indipendente in offerta.** Pronti a ingaggiare certifier ISCC indipendente per pre-audit del body se l'Unit lo ritiene utile.
- **Single point of contact.** Tutta la corrispondenza passerà attraverso un contact Crown Oil nominato per evitare comunicazione frammentata che ha contribuito al rigetto originale.

---

## 10. Registro rischi

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| DfT nega estensione | Medio | Alto (bundle Gen 2025 perso) | Track B procede comunque; bundle Gen e successivi salvabili per submission 2026 forward. |
| Autorizzazioni regolatorie Colombia non ottenibili nella finestra 30 gg | Media | Alto | Iniziare richieste settimana 1; escalation via consolato Colombia UK se ritardo; scope limitato a 3 collecting point riduce volume documenti richiesti. |
| PoS ISCC retroattivo Gennaio 2025 non concesso da certifier | Media | Alto | Ingaggiare certifier ISCC formalmente settimana 1; se rifiutato, documentare rifiuto e sottomettere evidence chain non-ISCC per procedura fallback RTFO. |
| Stock end-Jan 339.865 kg contestato da DfT come underdeclared input | Media | Alto | Annex D mandatorio + record interno OisteBio + dichiarazione formale Crown; offrire ispezione fisica facility se richiesta. |
| eRSV duplicates gennaio 2025 non riconciliabili | Bassa | Medio | Scope ridotto a singolo mese facilita riconciliazione; documentare limitazione sistema sorgente; fornire vista riconciliata da dati primari. |
| Audit interno (settimana 3) scopre ulteriori gap | Media | Alto | Standup giornalieri settimana 3 per far emergere gap presto; preferire ritardo submission che submission incompleta. |
| Submission Gennaio 2025 rigettata di nuovo | Bassa-Media | Alto | Pathway chiusa per bundle 2025. Trattenere output Track B per applicazioni 2026 forward; lezioni applicate. |

---

## 11. Plan B — pathway 2026 forward

Se il bundle Gennaio 2025 non è recuperabile, l'output Track B posiziona la pathway per applicazioni 2026 forward (inclusi i bundle 2025 Feb-Ago non sottomessi in questa finestra). Deliverable a valore duraturo:

- Sistema digital ingest con closure mass-balance giornaliera a zero, audit log ed export crittografico — affronta direttamente la critica DfT "information quality" per qualsiasi applicazione futura.
- Supply chain ricostruita con collecting point verificati e binding certificati ISCC — affronta critica "ISCC chain of custody".
- Autorizzazioni regolatorie Colombia per ciascun collecting point — affronta critica "feedstock provider registration".
- Offerta pre-audit certifier ISCC indipendente — affronta critica "submission incrementale e inconsistente".

Una applicazione 2026 costruita su questa base entra con posizione evidenziale marcatamente più forte di quanto facessero le applicazioni 2025.

---

## 12. Ownership piano e aggiornamenti

- **Crown Oil:** applicant di record; tutta comunicazione verso DfT.
- **OisteBio:** assemblaggio evidence, bonifica fornitori, liaison regolatoria Colombia.
- **Team digital ingest:** implementazione sistema DFT, report mass-balance, audit trail, pipeline OCR.

Questo piano è committato al repository sotto `docs/dft-action-plan-2026-05.md`. Aggiornamenti via commit git con riferimento alla sezione rilevante. Cambiamenti materiali (estensione concessa/rifiutata, aggiustamenti scope, requisiti regolatori aggiuntivi) riflessi in nuova versione del documento con changelog entry sotto.

---

## Changelog

- **v1 — 2026-05-13:** Piano iniziale committato (versione EN).
- **v2 — 2026-05-13:** Traduzione IT del piano; template comunicazioni DfT mantenuti in EN.
- **v3 — 2026-05-13:** Scope ridotto a **solo bundle RTFO-310125 (Gennaio 2025)**. Timeline compressa: estensione richiesta 14 mag → 13 giu 2026 (30 gg), checkpoint intermedio 30 mag, submission 13 giu. Annex A target Gennaio 2025 (non luglio). Annex D promosso a mandatorio (closing stock 339.865 kg). Bundle Feb/Mar/Jul/Ago 2025 trattenuti per submission successive o applicazioni 2026.
