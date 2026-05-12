# Piano d'azione DfT — RTFC 2025

**Oggetto:** Applicazione RTFC 2025 Crown Oil — development diesel da pneumatici a fine vita (Colombia / OisteBio).
**Contesto:** Lettera formale rigetto DfT ricevuta 9 marzo 2026 a seguito meeting del 5 marzo 2026. Bundle RTFO-310125, RTFO-280225, RTFO-310325, RTFO-310725, RTFO-210825 programmati cancellazione 13 marzo 2026. Deadline originale resubmission ROS: 14 maggio 2026.
**Data piano:** 13 maggio 2026.
**Owner piano:** Crown Oil (applicant) con OisteBio (produttore) e team digital ingest a supporto.
**Stato documento:** piano operativo, versione 1. Aggiornamenti via commit git man mano che il piano evolve.

---

## 1. Sintesi esecutiva

DfT ha rigettato l'intera pathway 2025 citando tre categorie di carenze: (a) chain of custody ISCC inadeguata, (b) evidence feedstock incompleta e mancanza production log di conversione, (c) submission inconsistenti e incrementali. L'Unit ha però lasciato esplicitamente una porta aperta: una resubmission coerente può essere depositata su ROS entro 14 maggio 2026, con verifica permessa dopo tale data previo consenso Unit.

Sono trascorsi due mesi dal rigetto senza comunicazione formale all'Unit. Il periodo è stato usato per ingaggiare specialista digital ingest e audit e ricostruire la base evidenziale a partire dati primari. Lavoro sufficientemente avanzato per:

- presentare mass-balance pienamente riconciliato per almeno un mese 2025 a standard audit;
- proporre finestra di rimedio definita 8 settimane con milestone delivery e checkpoint intermedio;
- impegnarsi a submission unica e coerente senza evidence incrementale o retrospettiva.

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
| Submission incrementale | Sì | Body unico coerente al 30 giugno 2026. Nessun upload parziale. |
| Inconsistenze su immagini sito produzione, capacità, date inizio | Sì | Pack documentazione sito consolidato da fonte autoritativa; una versione firmata per item. |
| Evidence retrospettiva | Sì | Ogni documento sottomesso pre-datato finestra resubmission e fonte indipendente. |

---

## 3. Strategia a due binari

### Track A — Richiesta estensione (immediato, basso costo, esito opzionale)

Sottomettere richiesta formale estensione a DfT LCF Delivery Unit il 13 maggio 2026 chiedendo che la deadline ROS del 14 maggio 2026 sia estesa al 30 giugno 2026 con checkpoint status intermedio al 15 giugno 2026.

Richiesta estensione preceduta da telefonata di cortesia al contact DfT nominato la mattina del 13 maggio 2026 per segnalare intent prima dell'arrivo della submission scritta.

La richiesta è accompagnata da un body iniziale di evidence (Annex A–E, vedi §6) che dimostra lo standard a cui sarà preparata la resubmission.

Probabilità successo incerta. I due mesi di silenzio e i precedenti motivi rigetto pesano contro; l'evidence sostanziale già preparata e lo scope limitato della richiesta pesano a favore. La richiesta è inviata comunque perché il costo è una giornata e l'upside è il recupero di cinque bundle 2025.

### Track B — Rimedio strutturato (indipendente esito Track A)

Indipendentemente dal fatto che DfT conceda o meno l'estensione, il lavoro di rimedio procede. I deliverable prodotti dal Track B sono:

- funzionalmente necessari per qualsiasi applicazione futura su questa pathway nel 2026 o oltre;
- input richiesti per la resubmission Track A se estensione concessa;
- utilizzabili come evidence fondazionale se Crown Oil e OisteBio decidono di ingaggiare un verifier ISCC indipendente (Bureau Veritas, SGS, DNV) per applicazioni forward.

Track B è il lavoro che crea valore. Track A è il tentativo di recuperare le applicazioni 2025 perse.

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
- Richiesta scritta formale di PoS ISCC retroattivo per gennaio-agosto 2025.
- Confermare certifier ISCC incaricato (Bureau Veritas Colombia / SGS Colombia / altro) e ingaggiare timeline.
- Identificare e documentare feedstock provider mal classificati nei record attuali (vedi §5).
- Sistema DFT: implementare tabella `collection_points`; implementare colonna `litres` nello schema production.

### Settimana 2 — 2026-05-26 → 2026-06-01

- Ricevere bozza PoS retroattivo o follow-up su richieste in sospeso.
- Avviare richieste documenti ANLA / Ministerio de Ambiente per ciascun collecting point.
- Sistema DFT: implementare campo `feedstock_provider_registration` nello schema supplier.
- Sistema DFT: implementare endpoint export PDF mass-balance audit-grade con hash crittografico.

### Settimana 3 — 2026-06-02 → 2026-06-08

- Legalizzazione consolare documenti Colombia (consolato UK, Bogotá).
- Traduzioni giurate EN.
- Sistema DFT: implementare generazione production log end-to-end (kg input → kg processed → litri output).
- Iniziare riconciliazione consistency eRSV gennaio-aprile 2025.

### Settimana 4 — 2026-06-09 → 2026-06-15 (Checkpoint intermedio)

- Compilare record production-to-litres per tutti e cinque i periodi bundle.
- Generare report mass-balance consolidati per tutti i periodi bundle.
- **Sottomettere status report intermedio scritto a DfT il 15 giugno 2026** (vedi §7 template).

### Settimana 5 — 2026-06-16 → 2026-06-22

- Se ingaggiato: kick-off pre-audit certifier ISCC indipendente.
- Assemblare pacchetti finali di submission per bundle (vedi §8 struttura).
- Generare snapshot crittografico dello stato database per garantire audit trail evidence.

### Settimana 6 — 2026-06-23 → 2026-06-29

- Audit interno del body assemblato.
- Cross-reference: ogni chilogrammo in mass-balance ↔ PoS ISCC ↔ registrazione provider.
- Formattazione finale per requisiti ROS.

### Day 30-of-window — 2026-06-30

- **Submission su ROS.** Body unico coerente, tutti e cinque i bundle.
- Notificare via email contact DfT nominato della submission.

### Post-submission — 2026-07 → 2026-08

- Rispondere prontamente alle domande di verifica DfT. Mai incrementalmente.
- Se approvato: applicare stesso standard d'ora in poi.
- Se rifiutato: pathway chiusa per i bundle 2025; deliverable Track B trattenuti per applicazioni 2026 forward.

---

## 5. Bonifica fornitori e collecting point

L'attuale sistema digital ingest riflette sette record supplier: ESENTTIA, SANIMAX, LITOPLAS, CIECOGRAS, BIOWASTE, ECODIESEL (dormant) e bucket aggregato "≤5 TON" per piccoli batch ISCC autodichiarati. La comprensione working di DfT identifica solo Litoplas, Biowaste ed Esenttia come collecting point.

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

### Annex A — Sample mass-balance riconciliato (luglio 2025)

Mass-balance giornaliero per luglio 2025 generato dal sistema digital ingest OisteBio. Closure giornaliera (input − production − by-products) uguale a zero su tutti i 31 giorni. Include dettaglio per-giorno e aggregato mensile. Formato: PDF, firmato, con hash SHA-256 per verifica integrità. Questo è il formato in cui tutti e cinque i mesi bundle saranno ri-presentati.

### Annex B — Diagramma supply chain

Diagramma che mostra quattro layer: origin point (dove applicabile), collecting point (certificati ISCC, post-bonifica), facility OisteBio (ricezione e conversione) e Crown Oil (end supplier UK). Include il PoS ISCC emesso a ogni passaggio.

### Annex C — Evidence register

Tabella di lavoro che elenca ogni documento richiesto per la resubmission, con stato corrente (disponibile, in progress, da raccogliere), owner e data target completamento. Item già disponibili: mass-balance digitale, audit log, spiegazione stock carry-over. Item da raccogliere: PoS ISCC retroattivo da ciascun collecting point, autorizzazioni regolatorie Colombia, record 2024 OCR'd / digitalizzati.

### Annex D — Spiegazione stock carry-over (gennaio / febbraio 2025)

Spiegazione scritta della varianza apparente nella closure di gennaio e febbraio 2025, che rappresenta carry-over simmetrico ±339.865 kg di stock feedstock da fine-2024 a inventario inizio-2025. La varianza si riconcilia a zero attraverso i due mesi ed è ricostruibile dai dati sorgente primari.

### Annex E — Piano milestone

Questo documento, sintetizzato in forma tabellare per il pacchetto richiesta estensione.

---

## 7. Checkpoint intermedio — 15 giugno 2026 (template)

```
Subject: RTFO 2025 EoL Tyres Pathway — Interim Status Report (per extension agreement)

Dear [Name],

Per the agreement of [DATE], please find Crown Oil's interim status report
against the Evidence Register submitted on 13 May 2026.

Items completed since 13 May:
- [each item from Annex C marked complete, with reference]

Items in progress:
- [each item, with revised completion target if any has slipped]

Items not yet started:
- [each item, with reason and target start]

Risks and dependencies:
- [legalisation timelines, certifier availability, third-party responsiveness]

Confirmation: we remain on track for submission by 30 June 2026.

[Signed, Crown Oil]
```

(Template in inglese — destinatario DfT UK.)

---

## 8. Struttura pacchetto submission finale — 30 giugno 2026

Per bundle (cinque bundle totali):

```
bundle_RTFO-XXXXXX/
├── 00_cover_letter.pdf                 (Crown Oil firmato)
├── 01_supply_chain_diagram.pdf         (origin → collecting point → OisteBio → Crown Oil)
├── 02_mass_balance_monthly.pdf         (export sistema DFT, giornaliero + aggregato mensile)
├── 03_iscc_pos_chain/
│   ├── litoplas_pos_YYYY-MM.pdf
│   ├── biowaste_pos_YYYY-MM.pdf
│   ├── esenttia_pos_YYYY-MM.pdf
│   └── oistebio_pos_to_crownoil_YYYY-MM.pdf
├── 04_feedstock_provider_authorisations/
│   ├── litoplas_anla_permit.pdf        (legalizzato + traduzione EN)
│   ├── biowaste_anla_permit.pdf
│   └── esenttia_anla_permit.pdf
├── 05_production_conversion_logs.pdf   (kg → litri, giornaliero, firmato)
├── 06_audit_trail_export.csv           (da tabella DFT audit_log)
├── 07_independent_audit_letter.pdf     (se certifier ISCC ingaggiato)
└── 08_evidence_index.pdf               (cross-reference docs ↔ punti rigetto DfT)
```

Una cover letter consolidata accompagna i cinque pacchetti bundle su ROS.

---

## 9. Commitment all'Unit

Subordinato alla concessione dell'estensione, Crown Oil e OisteBio si impegnano a:

- **Nessuna ulteriore submission incrementale.** Submission del 30 giugno 2026 sarà body unico coerente.
- **Nessuna evidence retrospettiva.** Ogni evidence sarà pre-datata finestra di assemblaggio e fonte indipendente.
- **Trasparenza intermedia.** Status report scritto fornito al 15 giugno 2026.
- **Verifica indipendente in offerta.** Pronti a ingaggiare certifier ISCC indipendente per pre-audit del body se l'Unit lo ritiene utile.
- **Single point of contact.** Tutta la corrispondenza passerà attraverso un contact Crown Oil nominato per evitare comunicazione frammentata che ha contribuito al rigetto originale.

---

## 10. Registro rischi

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| DfT nega estensione | Medio-Alta | Alto (bundle 2025 persi) | Track B procede comunque; 2026 forward salvabile. |
| Autorizzazioni regolatorie Colombia non ottenibili nella finestra | Media | Alto | Iniziare richieste settimana 1; escalation via consolato Colombia UK se ritardo. |
| PoS ISCC retroattivo non concesso da certifier | Media | Alto | Ingaggiare certifier ISCC formalmente settimana 1; se rifiutato, documentare rifiuto e sottomettere evidence chain non-ISCC per procedura fallback RTFO. |
| Record 2024 scritti a mano illeggibili | Alta (nota) | Medio | Pipeline OCR con verifica manuale; se illeggibili, documentare limitazione e sottomettere dichiarativamente. |
| eRSV duplicates gennaio-aprile 2025 non riconciliabili | Media | Medio | Documentare limitazione sistema sorgente; fornire vista riconciliata da dati primari. |
| Audit interno (settimana 6) scopre ulteriori gap | Media | Alto | Standup giornalieri settimana 5-6 per far emergere gap presto; preferire ritardo submission che submission incompleta. |
| Submission rigettata di nuovo | Media | Finale | Pathway chiusa per 2025. Trattenere output Track B per applicazioni 2026 forward. |

---

## 11. Plan B — pathway 2026 forward

Se i bundle 2025 non sono recuperabili, l'output Track B posiziona la pathway per applicazioni 2026 forward. Deliverable a valore duraturo:

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
