# Piano attività — 5 working days extra time DfT

**Contesto:** DfT LCF Delivery Unit ha concesso a Crown Oil **5 working days** di extra time sulla deadline ROS originale del 14 maggio 2026. Estensione inferiore ai 30 giorni richiesti dal piano `dft-action-plan-2026-05.md` v3. Il presente documento sostituisce la timeline §4 di quel piano per la sola finestra di submission; struttura bundle (§8), commitment (§9), evidence (§6) restano validi.
**Scope confermato di lavoro:** **Solo Gennaio 2025** — bundle singolo RTFO-310125. Bundle Feb/Mar/Jul/Ago 2025 fuori scope (irraggiungibili in 5 wd; trattenuti per applicazioni successive).
**Data piano:** 2026-05-15.
**Owner:** Crown Oil (applicant) + OisteBio (produttore) + team digital ingest.

---

## 1. Assunzioni e item da confermare entro fine giornata 15 maggio

Il piano procede su queste assunzioni di lavoro. Se cliente o Crown Oil hanno informazione contraria, segnalare entro fine giornata di oggi per riallineamento.

| Item | Assunzione di lavoro | Necessaria conferma |
|---|---|---|
| Decorrenza 5 wd | 15 mag 2026 (giorno successivo deadline originale 14 mag) | Crown Oil — lettera/email formale DfT |
| Deadline submission ROS | **Giovedì 21 maggio 2026, 23:59 UK time** | Crown Oil |
| Scope concesso | Solo Gennaio 2025 (bundle RTFO-310125) | Crown Oil — verificare wording DfT |
| PoS ISCC retroattivo | **Non perseguibile in 5 wd** — gap dichiarato in cover letter e impegno post-acceptance | OisteBio + Crown Oil — accordo strategico |
| Autorizzazioni regolatorie Colombia | **Non legalizzabili in 5 wd** — copie semplici + impegno legalizzazione post | OisteBio — fornire copie esistenti |
| Verifier ISCC indipendente | **Non ingaggiabile in 5 wd** — offerta scritta nella cover letter, scope pre-audit Gen 2025 | Crown Oil |
| Stock carry-over 339.865 kg | Annex D mandatorio (già documentato in memoria progetto) | Team ingest — finalizzare PDF |
| Telefonata + email 13 maggio | Già inviate (da action plan v3) | Crown Oil — confermare timestamp |

---

## 2. Strategia 5 wd — sintesi

Cinque working days non sono sufficienti per chiudere tutti i punti del rigetto DfT con evidence completa di prima fascia. Strategia operativa:

1. **Submission entro deadline** del bundle Gennaio 2025 con evidence primaria completa generata dal sistema digital ingest (mass-balance riconciliato, audit log, production conversion log kg→litri, stock carry-over Annex D, supply chain diagram).
2. **Dichiarazione esplicita dei gap residui** nella cover letter: (a) PoS ISCC retroattivo per Gen 2025 in raccolta presso certifier Colombia, target post-acceptance; (b) autorizzazioni ANLA/Ministerio de Ambiente in legalizzazione consolare, copie semplici incluse nel pack; (c) pre-audit certifier ISCC indipendente offerto su richiesta Unit.
3. **Posizionamento per follow-up:** la submission è strutturata come "evidence base completa lato produttore + gap regolatori formalizzati e in chiusura" — non come submission incompleta.

Compromesso accettato consapevolmente: probabilità accettazione inferiore al piano 30 gg, ma submission tempestiva è preferibile a no-submission. Il lavoro Track B prosegue post-21 maggio indipendentemente dall'esito.

---

## 3. Timeline giornaliera

Tutte le date orario UK. Working days = Lun–Ven.

### Day 1 — Venerdì 2026-05-15 (oggi)

| Owner | Attività | Output |
|---|---|---|
| Crown Oil | Conferma scritta a DfT di ricezione estensione + accettazione condizioni | Email con timestamp |
| Crown Oil | Conferma item §1 (decorrenza, scope, deadline esatta) | Replica su questo documento |
| Team ingest | Implementare colonna `litres` schema `production` + migration `0009_production_litres.py` | Migration applicata in locale + prod |
| Team ingest | Backfill `litres` per Gennaio 2025 da fattore di conversione produzione OisteBio | Daily production Gen 2025 con `litres` popolato |
| Team ingest | Generare prima draft export PDF mass-balance Gennaio 2025 (giornaliero + aggregato) | `02_mass_balance_january_2025_v1.pdf` |
| OisteBio | Inviare copie semplici (anche non legalizzate) autorizzazioni regolatorie disponibili per Litoplas/Biowaste/Esenttia | File trasmessi al team ingest |
| OisteBio | Richiesta scritta formale a certifier ISCC Colombia per PoS retroattivo Gen 2025 | Email con timestamp (cc Crown Oil) |
| Crown Oil | Draft cover letter v0 — dichiarazione scope Jan-only + gap residui formalizzati | `00_cover_letter_v0.md` |

### Day 2 — Lunedì 2026-05-18

| Owner | Attività | Output |
|---|---|---|
| Team ingest | Endpoint export PDF audit-grade con SHA-256 hash crittografico | Endpoint `/api/reports/mass-balance/export` + hash file |
| Team ingest | Rigenerare Annex A (mass-balance) con hash crittografico finale | `02_mass_balance_january_2025.pdf` + `.sha256` |
| Team ingest | Generare Annex D — explanation closing stock 339.865 kg | `07_stock_carryover_explanation.pdf` |
| Team ingest | Production conversion log kg→litri Gennaio 2025 (firmato OisteBio) | `05_production_conversion_logs_january_2025.pdf` |
| OisteBio | Bonifica fornitori limitata a lotti Gennaio 2025 (soft-delete riclassificazioni, audit log preservato) | Migration `0010_supplier_rectification_jan2025.py` applicata |
| Crown Oil | Cover letter v1 — review legale interno | `00_cover_letter_v1.pdf` |

### Day 3 — Martedì 2026-05-19

| Owner | Attività | Output |
|---|---|---|
| Team ingest | Audit log export CSV Gennaio 2025 da tabella `audit_log` | `06_audit_trail_export_january_2025.csv` |
| Team ingest | Supply chain diagram Gen 2025 (origin → collecting point → OisteBio → Crown Oil) | `01_supply_chain_diagram.pdf` |
| OisteBio | Consolidare copie semplici autorizzazioni regolatorie + nota di stato legalizzazione in corso | `04_feedstock_provider_authorisations/` (copie + nota stato) |
| Team ingest | Evidence index — cross-reference docs ↔ punti rigetto DfT | `09_evidence_index.pdf` |
| Crown Oil | Cover letter v2 — incorporare evidence definitive + lista gap residui esatta | `00_cover_letter_v2.pdf` |

### Day 4 — Mercoledì 2026-05-20

| Owner | Attività | Output |
|---|---|---|
| Team ingest + OisteBio + Crown Oil | **Audit interno bundle completo** — cross-reference: ogni kg Gennaio in mass-balance ↔ daily_input ↔ supplier ↔ PoS o gap dichiarato | Checklist firmata |
| Team ingest | Fix di gap emersi in audit interno; rigenerare export con hash finale | `02_mass_balance_january_2025_FINAL.pdf` + hash |
| Crown Oil | Cover letter FINAL firmata | `00_cover_letter.pdf` (firmato) |
| Team ingest | Snapshot crittografico stato database post-bonifica | `db_snapshot_2026-05-20.sql.gz` + SHA-256 |
| Crown Oil | Dry-run formattazione bundle su requisiti ROS | Bundle in struttura `bundle_RTFO-310125/` |

### Day 5 — Giovedì 2026-05-21

| Orario UK | Owner | Attività |
|---|---|---|
| Mattina | Team ingest | Verifica integrità finale bundle: tutti i file presenti, hash verificati, dimensioni corrette |
| Mattina | Crown Oil | Telefonata di cortesia al contact DfT nominato segnalando submission imminente |
| Pomeriggio | Crown Oil | **Submission bundle RTFO-310125 su ROS** |
| EOD | Crown Oil | Email notifica formale al contact DfT confermando submission + lista allegati + hash file principale |

**Buffer:** zero. Slittamento di un giorno = mancata deadline = pathway 2025 chiusa.

---

## 4. Bundle finale — invariato da action plan §8

Struttura bundle `bundle_RTFO-310125/` invariata da `dft-action-plan-2026-05.md` §8. Modifiche solo su due item:

- `03_iscc_pos_chain/` — **non presente nel bundle finale**. Sostituito da `03_iscc_pos_status.pdf` che documenta richiesta retroattiva inoltrata 15 maggio + risposta certifier (se ricevuta entro 20 maggio) + impegno consegna post-acceptance.
- `04_feedstock_provider_authorisations/` — copie semplici + nota di stato legalizzazione consolare in corso, ETA. Non legalizzate entro 21 maggio.
- `08_independent_audit_letter.pdf` — non presente. Sostituito da paragrafo dedicato in cover letter che offre pre-audit ISCC indipendente su richiesta Unit.

Tutti gli altri item (`00`, `01`, `02`, `05`, `06`, `07`, `09`) presenti e completi.

---

## 5. Gap residui — dichiarazione esplicita nella cover letter

Wording proposto per cover letter (sezione "Outstanding items"):

1. **Retrospective ISCC Proofs of Sustainability for January 2025 inputs.** Formal request submitted to ISCC-accredited certifier in Colombia on 15 May 2026. Status documented in `03_iscc_pos_status.pdf`. Crown Oil and OisteBio commit to forwarding PoS chain to the Unit within 30 days of bundle acceptance, or to documenting refusal and engaging fallback evidence procedure.
2. **Feedstock provider regulatory authorisations (Colombia).** Simple copies of ANLA / Ministerio de Ambiente permits for Litoplas, Biowaste and Esenttia are included in `04_feedstock_provider_authorisations/`. Consular legalisation (UK consulate, Bogotá) and sworn EN translations are in progress; legalised originals will be transmitted within 30 days of bundle acceptance.
3. **Independent ISCC verifier pre-audit.** Crown Oil offers to engage an independent ISCC verifier (Bureau Veritas Colombia / SGS Colombia) for pre-audit of the January 2025 evidence pack, on request from the Unit. Engagement can be initiated within 5 working days of Unit confirmation.

---

## 6. Registro rischi 5-wd specifico

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Slittamento Day 1 (litres schema + backfill) | Media | Alto (a cascata su tutto) | Priorità assoluta oggi; pair-programming se necessario; rollback plan se backfill produce inconsistenze |
| Certifier ISCC non risponde a richiesta PoS entro 20 maggio | Alta | Medio | Bundle non dipende da risposta; gap dichiarato in cover letter; risposta o sua assenza documentata in `03_iscc_pos_status.pdf` |
| Bonifica fornitori (Day 2) introduce regressione closure mass-balance | Bassa | Alto | Eseguire query closure pre/post migration; rollback immediato se delta > tolerance; preferire scope ridotto (solo riclassificazioni non controverse) |
| Hash crittografico finale (Day 4) cambia per fix audit interno | Alta | Basso | Cover letter cita hash come "manifest hash"; lista hash per file in evidence index `09_` |
| DfT rigetta nuovamente bundle | Media | Alto | Pathway 2025 chiusa per Gennaio; deliverable Track B trattenuti per applicazioni 2026 forward; lezioni applicate |
| Cliente non risponde a item §1 entro fine 15 maggio | Media | Alto | Procedere su assunzioni di lavoro; flaggare ogni decisione critica nel commit log |
| Bug bloccante in export PDF / migration `litres` | Bassa | Alto | Test E2E su sample Gennaio 2025 prima di applicare prod; fallback: export manuale da query SQL diretta |

---

## 7. Post-submission — 22 maggio in avanti

- Rispondere prontamente e singolarmente alle domande di verifica DfT sul bundle Gennaio 2025. Mai incrementalmente.
- Procedere con Track B (PoS retroattivo, legalizzazione consolare, ingaggio certifier indipendente) indipendentemente da esito immediato.
- Se bundle Gennaio accettato: avviare assemblaggio bundle successivi (Feb/Mar/Jul/Ago 2025) con stesso standard; finestra da concordare con Unit.
- Se bundle Gennaio rigettato: applicare lezioni a applicazione RTFO 2026 forward; pathway 2025 chiusa.

---

## 8. Ownership

- **Crown Oil:** applicant di record; tutta comunicazione verso DfT; cover letter; submission ROS; conferma scope/deadline.
- **OisteBio:** evidence operativa Girardot; bonifica fornitori; richieste a certifier ISCC + autorità regolatorie Colombia; copie autorizzazioni.
- **Team digital ingest (BiNova):** schema `litres`, export PDF audit-grade con hash, audit log CSV, supply chain diagram, evidence index, snapshot DB, audit interno bundle Day 4.

---

## 9. Aggiornamenti

Aggiornamenti via commit git con riferimento alla sezione rilevante. Per cambiamenti materiali (es. estensione ulteriormente accorciata, scope ridefinito, gap risolto inaspettatamente) aggiornare con nuova entry in changelog sotto.

---

## Changelog

- **v1 — 2026-05-15:** Piano iniziale 5 working days. Sostituisce timeline §4 di `dft-action-plan-2026-05.md` v3 per la finestra 15-21 maggio 2026. Submission target: 21 maggio 2026 EOD, bundle RTFO-310125 (Gennaio 2025) singolo coerente. PoS retroattivo + legalizzazione consolare + pre-audit ISCC dichiarati come gap residui post-acceptance.
