# Piano attività — 5 working days extra time DfT

**Contesto:** DfT LCF Delivery Unit ha concesso a Crown Oil **5 working days** di extra time sulla deadline ROS originale del 14 maggio 2026. Estensione inferiore ai 30 giorni richiesti dal piano `dft-action-plan-2026-05.md` v3. Il presente documento sostituisce la timeline §4 di quel piano per la sola finestra di submission; struttura bundle (§8), commitment (§9), evidence (§6) restano validi.
**Scope confermato di lavoro:** **Solo Gennaio 2025** — bundle singolo RTFO-310125. Bundle Feb/Mar/Jul/Ago 2025 fuori scope (irraggiungibili in 5 wd; trattenuti per applicazioni successive).
**Data piano:** 2026-05-15.
**Owner:** Crown Oil (applicant) + OisteBio (produttore) + team digital ingest.

---

## 0. Stato sistema DFT — verifica 2026-05-15

Audit codice + DB eseguito 2026-05-15 prima di redigere v3:

| Componente | Stato reale | Note |
|---|---|---|
| Migrations Alembic | **5 applicate** (0001-0005), DB su `0005` | CLAUDE.md dichiara "8 migrations" — obsoleto. Prossima = `0006_`, non `0009/0010` come scritto in v1/v2 |
| Colonna `litres` produzione | **Già computed in MV** via `product_densities` lookup (migration 0005) — EU 0.78, PLUS 0.856 da EAD Andrea Olga, confermate 2026-05-13 | `eu_prod_litres`/`plus_prod_litres`/`total_prod_litres` esposti in `mv_mass_balance_daily/monthly` e schema reports. Day 1 "implementare litres" obsoleto |
| Mass-balance Gennaio 2025 | **Già in MV** — input 3.383.177 kg, eu_prod 760.828 kg / 975.420 l, plus 1.308.624 kg / 1.528.766 l, closure −10,05% (carry-over noto 339.865 kg) | Da esporre come PDF audit-grade |
| Endpoint export PDF + SHA-256 | **Inesistente** — zero `weasyprint`/`reportlab`/`hashlib` nel backend | Da costruire ex novo |
| Endpoint export CSV audit_log | **Inesistente** — endpoint `/admin/audit-log` ritorna solo JSON | Da aggiungere `?format=csv` con StreamingResponse |
| Tabelle DB | `users`, `suppliers`, `supplier_certificates`, `contracts`, `certificates`, `daily_inputs`, `daily_production`, `audit_log`, `product_densities`, `alembic_version` | Schema completo per scope Gen 2025 |
| Materialized views | `mv_mass_balance_daily`, `mv_mass_balance_monthly` | Refresh AUTOCOMMIT (vedi `routers/mass_balance.py`) |
| Container produzione | `dft-back` + `dft-project_db_1` healthy da 4+ giorni | OK |

Implicazione: scope tecnico effettivo del piano è **PDF export + CSV audit export + bonifica fornitori migration + snapshot script**. Tutto il resto (mass-balance computation, densities, MV, audit log persistence) è già pronto.

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

Tutte le date orario UK. **7 giorni di calendario** lavorati consecutivamente — team OisteBio + ingest operativo anche sabato 16 e domenica 17 maggio. Working days ufficiali DfT (5 wd) = Lun–Ven; weekend lavorato è capacità extra del team, non riconosciuto formalmente da DfT ma usato per buffer e parallelizzazione.

### Day 1 — Venerdì 2026-05-15 (oggi)

| Owner | Attività | Output |
|---|---|---|
| Crown Oil | Conferma scritta a DfT di ricezione estensione + accettazione condizioni | Email con timestamp |
| Crown Oil | Conferma item §1 (decorrenza, scope, deadline esatta) | Replica su questo documento |
| Team ingest | **Verifica `litres` in MV** (già computed via `product_densities`, migration 0005) + decidere se persistere come colonna fisica `daily_production.litres_eu`/`litres_plus` per audit immutabile DfT | Decisione documentata; eventuale migration `0006_persist_litres.py` se persistenza richiesta |
| Team ingest | **Costruire ex novo endpoint export PDF audit-grade** — WeasyPrint + template Jinja per mass-balance giornaliero + aggregato mensile; calcolo SHA-256 a generazione; aggiungere dipendenza `weasyprint` a `requirements.txt` | Endpoint `/api/reports/mass-balance/export?month=2025-01&format=pdf` + hash side-car |
| Team ingest | Prima draft PDF mass-balance Gennaio 2025 via nuovo endpoint | `02_mass_balance_january_2025_v1.pdf` + `.sha256` |
| OisteBio | Inviare copie semplici (anche non legalizzate) autorizzazioni regolatorie disponibili per Litoplas/Biowaste/Esenttia | File trasmessi al team ingest |
| OisteBio | Richiesta scritta formale a certifier ISCC Colombia per PoS retroattivo Gen 2025 | Email con timestamp (cc Crown Oil) |
| Crown Oil | Draft cover letter v0 — dichiarazione scope Jan-only + gap residui formalizzati | `00_cover_letter_v0.md` |

### Day 2 — Sabato 2026-05-16 (weekend lavorato)

| Owner | Attività | Output |
|---|---|---|
| Team ingest | Hardening endpoint export PDF Day 1 — paginazione mese, header firma, footer hash, template Annex A definitivo | Endpoint stabile + template `templates/reports/mass_balance.html` |
| Team ingest | Rigenerare Annex A con hash definitivo v2 | `02_mass_balance_january_2025_v2.pdf` + `.sha256` |
| Team ingest | Annex D — explanation closing stock 339.865 kg (composizione 17 K-only rows JANUARY2025, riferimento memoria progetto) | `07_stock_carryover_explanation.pdf` |
| OisteBio | Bonifica fornitori limitata a lotti Gennaio 2025 (soft-delete riclassificazioni, audit log preservato) | Migration `0006_supplier_rectification_jan2025.py` applicata + audit_log popolato |
| Team ingest | Verifica closure mass-balance pre/post bonifica fornitori — refresh MV + confronto delta | Report comparativo, rollback se delta > 0.01% |

### Day 3 — Domenica 2026-05-17 (weekend lavorato)

| Owner | Attività | Output |
|---|---|---|
| Team ingest | Production conversion log kg→litri Gennaio 2025 — PDF dedicato che mostra densities lookup (EU 0.78, PLUS 0.856) + formula + riga per giorno (firmato OisteBio) | `05_production_conversion_logs_january_2025.pdf` |
| Team ingest | **Aggiungere endpoint CSV su `/admin/audit-log`** (StreamingResponse) — filtro `?since=2025-01-01&until=2025-01-31` | Endpoint + `06_audit_trail_export_january_2025.csv` per Gennaio 2025 |
| Team ingest | Supply chain diagram Gen 2025 (origin → collecting point → OisteBio → Crown Oil) | `01_supply_chain_diagram.pdf` |
| OisteBio | Consolidare copie semplici autorizzazioni regolatorie + nota di stato legalizzazione in corso | `04_feedstock_provider_authorisations/` (copie + nota stato) |

### Day 4 — Lunedì 2026-05-18

| Owner | Attività | Output |
|---|---|---|
| Crown Oil | Cover letter v1 — review legale interno | `00_cover_letter_v1.pdf` |
| Team ingest | Evidence index — cross-reference docs ↔ punti rigetto DfT | `09_evidence_index.pdf` |
| Team ingest | `03_iscc_pos_status.pdf` — documenta richiesta + eventuale risposta certifier ricevuta nel weekend | File firmato |
| Team ingest + OisteBio | **Pre-audit interno parziale** — verifica completezza Annex A/B/C/D + production log + audit CSV | Checklist gap |
| Crown Oil | Allineamento OisteBio su gap emersi pre-audit | Lista azioni Day 5 |

### Day 5 — Martedì 2026-05-19

| Owner | Attività | Output |
|---|---|---|
| Team ingest | Fix di gap emersi in pre-audit Day 4; rigenerare export se necessario | `02_mass_balance_january_2025_v3.pdf` + hash |
| Crown Oil | Cover letter v2 — incorporare evidence definitive + lista gap residui esatta | `00_cover_letter_v2.pdf` |
| OisteBio | Follow-up scritto a certifier ISCC se nessuna risposta entro lunedì sera | Email con timestamp |
| Team ingest | Snapshot crittografico DB post-bonifica preliminare — `pg_dump dft \| gzip` + `sha256sum` | `db_snapshot_2026-05-19.sql.gz` + `.sha256` |

### Day 6 — Mercoledì 2026-05-20

| Owner | Attività | Output |
|---|---|---|
| Team ingest + OisteBio + Crown Oil | **Audit interno bundle completo** — cross-reference: ogni kg Gennaio in mass-balance ↔ daily_input ↔ supplier ↔ PoS o gap dichiarato | Checklist firmata |
| Team ingest | Fix finale gap emersi; rigenerare export con hash FINAL | `02_mass_balance_january_2025_FINAL.pdf` + hash |
| Crown Oil | Cover letter FINAL firmata | `00_cover_letter.pdf` (firmato) |
| Team ingest | Snapshot crittografico stato database FINAL | `db_snapshot_2026-05-20.sql.gz` + SHA-256 |
| Crown Oil | Dry-run formattazione bundle su requisiti ROS | Bundle in struttura `bundle_RTFO-310125/` |

### Day 7 — Giovedì 2026-05-21 (deadline DfT)

| Orario UK | Owner | Attività |
|---|---|---|
| Mattina | Team ingest | Verifica integrità finale bundle: tutti i file presenti, hash verificati, dimensioni corrette |
| Mattina | Crown Oil | Telefonata di cortesia al contact DfT nominato segnalando submission imminente |
| Pomeriggio | Crown Oil | **Submission bundle RTFO-310125 su ROS** |
| EOD | Crown Oil | Email notifica formale al contact DfT confermando submission + lista allegati + hash file principale |

**Buffer:** weekend (Day 2-3) usato per parallelizzare evidence operativa e bonifica fornitori; settimana lavorativa (Day 4-6) usata per cover letter cycles + audit interno + fix. Slittamento di un giorno su Day 6 ancora recuperabile mattina Day 7; slittamento Day 7 = mancata deadline = pathway 2025 chiusa.

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
| Slittamento Day 1 (build endpoint PDF + WeasyPrint setup) | Media | Alto (a cascata su tutto) | Priorità assoluta oggi; litres già pronto = risorse libere su PDF; fallback HTML→print-to-PDF browser headless se WeasyPrint setup lento; weekend Day 2-3 recupera parzialmente |
| WeasyPrint dipendenze sistema (cairo/pango/gdk-pixbuf) mancanti in container | Media | Medio | Verificare oggi `apt list --installed` in dft-back; rebuild Dockerfile con dipendenze se mancanti; fallback `reportlab` (pure Python, no system deps) |
| Certifier ISCC non risponde a richiesta PoS entro 20 maggio | Alta | Medio | Bundle non dipende da risposta; gap dichiarato in cover letter; risposta o sua assenza documentata in `03_iscc_pos_status.pdf` |
| Bonifica fornitori (Day 2 sabato) introduce regressione closure mass-balance | Bassa | Alto | Eseguire query closure pre/post migration; rollback immediato se delta > 0.01%; preferire scope ridotto (solo riclassificazioni non controverse) |
| Hash crittografico FINAL (Day 6) cambia per fix audit interno | Alta | Basso | Cover letter cita hash come "manifest hash"; lista hash per file in evidence index `09_`; rigenerazione hash è veloce |
| DfT rigetta nuovamente bundle | Media | Alto | Pathway 2025 chiusa per Gennaio; deliverable Track B trattenuti per applicazioni 2026 forward; lezioni applicate |
| Cliente non risponde a item §1 entro fine 15 maggio | Media | Alto | Procedere su assunzioni di lavoro; flaggare ogni decisione critica nel commit log |
| Bug bloccante in export PDF / migration `litres` | Bassa | Alto | Test E2E su sample Gennaio 2025 prima di applicare prod; fallback: export manuale da query SQL diretta |
| Team OisteBio o ingest non disponibile sabato/domenica come previsto | Media | Medio | Ridistribuire task weekend su Day 4-5; rinunciare a snapshot DB preliminare Day 5; mantenere Day 6 audit interno e Day 7 submission |

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
- **v2 — 2026-05-15:** Timeline estesa a 7 giorni di calendario lavorati consecutivamente (sabato 16 + domenica 17 maggio inclusi come capacità team, non riconosciuti formalmente da DfT). Day 1-7 rinumerati: Day 2 sabato (export endpoint + hash + bonifica fornitori), Day 3 domenica (production log + audit CSV + supply chain + autorizzazioni). Working days DfT ufficiali Lun-Ven invariati. Risk register aggiornato con scenario weekend non disponibile.
- **v3 — 2026-05-15:** §0 aggiunto con audit stato sistema reale. Correzioni materiali: (a) `litres` già pronto via `product_densities` lookup in MV (migration 0005); Day 1 task riallineato a "verifica + decisione persistenza colonna fisica" invece di "implementare". (b) Numeri migration corretti: prossima `0006_`, non `0009`/`0010`. (c) Endpoint export PDF + SHA-256 dichiarato esplicitamente come "costruire ex novo" — zero `weasyprint`/`hashlib` nel backend attuale. (d) CSV audit_log: aggiunto come task Day 3 (endpoint esiste solo JSON). (e) Risk register: aggiunto rischio dipendenze sistema WeasyPrint (cairo/pango), con fallback reportlab. (f) Closure −10,05% Gennaio + 339.865 kg carry-over confermati come dato già in MV.
