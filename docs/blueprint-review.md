# DFT — Reviewer Pass v1 — Blueprint + Sprint Plan + Plane Payloads

> Data: 2026-05-15
> Reviewer: reviewer agent, pass v1
> Inputs reviewed:
> - `docs/blueprint-activities.md` (architect, 6 epic / 68 stories)
> - `docs/sprint-plan.md` (PM, 5 sprint window)
> - `docs/plane-issue-payloads.json` (orchestrator-ready, 68 payload)
> - `docs/rtfo-gap-analysis.it.md` v2 (gap §3.1-3.7, fasi 1-4)
> - `docs/sprint-3-frontend.md` (DFTEN-72..81 pre-esistenti)
> - `docs/dft-action-plan-2026-05.md` v3
> - `docs/dft-5wd-activity-plan.md` v3
> - `CLAUDE.md`, `BLUEPRINT.md` v0.1, baseline live (5 migrations 0001-0005)

---

## Verdict — YELLOW (ship after minor patches)

**Razionale (1 riga):** zero blocker hard; copertura gap RTFO §3.1-3.7 completa e tracciata; 4 warning di igiene (AC verifica-style su S2.11, bundling 3 migrations in S5.3, conditional 0007 in S1.1 senza follow-up story, S6.8 XL non splittato); le 5 observation sono drift documentale non bloccante. POST a Plane può procedere dopo le 4 azioni nella sezione **Recommended actions**.

---

## 1. Coverage matrix — Gap §3 → Story IDs

| Gap area (rtfo-gap-analysis §) | Obbligazione RTFO | Story copertura | Sprint | Stato |
|---|---|---|---|---|
| §3.1 Feedstock identity & provenance | List of Feedstocks, ELT classification, chain-of-custody, waste hierarchy, Q3 ELT LCF | E3-S3.1, S3.2, S3.3, S3.4, S3.5, S3.6 (collection_points) + E1-S1.14 (auth folder Gen2025) | S3 (E1)+S4 (E3) | ✅ |
| §3.2 GHG / Carbon Intensity (Annex D) | counterfactual + 65% saving + RED II Annex V | E6-S6.1..S6.9 (modelli, calculator, PDF Annex D, frontend worksheet, regression test) | S7 | ✅ |
| §3.3 RTFC inventory management | rtfc_batches, rtfc_events, carry-over cap 25%, dRTFC, ledger | E4-S4.1..S4.10, E4-S4.11 (trade ledger), E4-S4.13 (notification certifier) | S5 | ✅ |
| §3.4 Off-takers + verifiers | obblighi verification, verifier registry | E5-S5.1 off_takers, S5.2 verifiers (anagrafica + UI in S5.6 — flag dependency cross-epic) | S6 | ⚠️ vedi WARN-3 |
| §3.5 ROS export & submission | XML / CSV ROS format, ack tracking | E5-S5.3 (mig 0018 ros_exports), S5.4 service, S5.7 endpoint, S5.8 frontend | S6 | ✅ |
| §3.6 N/A per ELT (FQD Article 7a, sustainability ISCC) | non applicabile, escluso esplicitamente nel blueprint §2 E1 Scope OUT | — (deliberatamente non in scope) | — | ✅ |
| §3.7 Obligation lifecycle (15 Sep, £0.50/£0.80 buyout, reminders) | obligation_periods seed, buyout_events, scheduler reminders | E4-S4.3 (mig 0013 obligation_periods), E5-S5.3 (mig 0016 buyout_events + 0017 reminders), S5.5 scheduler | S5/S6 | ✅ |

**Sprint 3 frontend (DFTEN-72..81) — assorbimento:** S3-1..S3-10 → E2-S2.1..S2.10 (mappatura 1:1 confermata); aggiunto **E2-S2.11** "DoD verification + deploy smoke test" — quindi 11 storie totali in E2 (non 10). Vedi OBS-1.

**Open decisions D1-D10 — tutte tracciate** come story con `_priority` urgent o linkate via `_blocked_by`:
- D1 timeline 5wd → E1-S1.1 / blocca E1 entire
- D2 persistenza litres → E1-S1.1
- D3 buyout strategy → E5-S5.5
- D4 ELT LCF Q3 → E3-S3.1
- D5 Crown Oil contract basis → E4-S4.1
- D6 verifier shortlist → E5-S5.2
- D7 ROS XML vs CSV format → E5-S5.4
- D8 Annex D approach → E6-S6.1
- D9 reminder channel (email/Slack) → E5-S5.5 task
- D10 ANLA/Min.Ambiente paths → E1-S1.14

**Migration map (0006-0020) — owning story:**

| Migration | Story | Sprint |
|---|---|---|
| 0006 supplier_rectification_jan2025 | E1-S1.7 | S3 |
| 0007 persist_production_litres (conditional) | E1-S1.1 → no follow-up story if "persist" — vedi WARN-2 | S3 |
| 0008 feedstocks | E3-S3.2 | S4 |
| 0009 daily_inputs.feedstock_id back-fill | E3-S3.5 | S4 |
| 0010 collection_points | E3-S3.7 | S4 |
| 0011 rtfc_batches | E4-S4.1 | S5 |
| 0012 rtfc_events | E4-S4.2 | S5 |
| 0013 obligation_periods + seed | E4-S4.3 | S5 |
| 0014 contract→rtfc linkage | E4-S4.4 | S5 |
| 0015 off_takers + verifiers | E5-S5.1+S5.2 | S6 |
| 0016 buyout_events | E5-S5.3 (bundled) | S6 |
| 0017 reminders | E5-S5.3 (bundled) | S6 |
| 0018 ros_exports | E5-S5.3 (bundled) | S6 |
| 0019 ghg_calculations | E6-S6.2 | S7 |
| 0020 ghg_inputs | E6-S6.3 | S7 |

⚠️ regola architetto "ogni migration = deliverable di una sola story" violata in maniera debole da E5-S5.3 (3 migrations in una story). Vedi WARN-4.

---

## 2. Findings

### 2.1 Blockers (must-fix prima del POST) — **0**

Nessuno.

### 2.2 Warnings (fix raccomandato; non blocca POST se accettati esplicitamente) — **4**

**WARN-1 — E2-S2.11 AC verification-style, non testabile pass/fail**
- Story: `[E2-S2.11] Sprint 3 DoD verification + deploy smoke test`
- Citazione AC payload: "Tutti i 10 issue chiusi in Plane" + "smoke test su oistebio.usenexos.com".
- Problema: "tutti chiusi" è osservazione di stato, non check eseguibile. Manca lista esplicita check (login, sidebar, mass-balance render, suppliers CRUD, certificates upload, audit JSON tail, ecc.).
- Fix proposto: riscrivere AC come checklist 8 punti concreti (es. "POST /auth/login → 200 + cookie", "GET /app/reports/mass-balance → render tabella Gen 2025 con totali kg/L", "GET /app/audit → ultimi 50 eventi", ecc.).

**WARN-2 — Conditional 0007 in S1.1 senza follow-up story esplicita**
- Story: `[E1-S1.1] Decisione persistenza litres su daily_production`
- Citazione AC: "Se 'persistere' → migration 0007 pronta come follow-up; Se 'MV-only' → nessuna migration".
- Problema: il ramo "persistere" presuppone che esista (o sarà creata al volo) una story `[E1-S1.X] Migration 0007 persist litres`. Nel payload set non esiste; D2 si risolve Day 1 EOD.
- Fix proposto: creare contingente `[E1-S1.6b] Migration 0007 persist_production_litres` con `_blocked_by: ["E1-S1.1"]` e flag "_conditional: D2=persist". O documentare nello story body che se decisione=persist, l'orchestrator crea la story addizionale a runtime.

**WARN-3 — E5-S5.6 dipendenza cross-epic non flaggata urgent**
- Story: `[E5-S5.6] Frontend off_takers + verifiers admin pages`
- Problema PM-flagged: pagine UI off_takers/verifiers servono già a E4 (RTFC ledger ha bisogno di off_taker_id selectable). S5.6 attualmente schedulato Sprint 6 (post-E4). Se E4 stories scrivono righe rtfc_events serve UI o seed manuale.
- Fix proposto: o anticipare S5.1+S5.2 (anagrafica) a Sprint 5 (lasciando solo le pagine UI in S6), o aggiungere in E4-S4.5 un seed admin-CLI come fallback. Documentare scelta in D6.

**WARN-4 — E5-S5.3 bundla 3 migrations in una story**
- Story: `[E5-S5.3] Migrations 0016 buyout_events + 0017 reminders + 0018 ros_exports`
- Problema: regola architetto §0 / blueprint convenzioni "each migration = deliverable of exactly one story". Bundle indebolisce traceability e rollback granulare.
- Razionale di difesa (architetto): tre tabelle sono infrastruttura E5 prerequisite, accoppiate per Phase 3. Accettabile se documentato.
- Fix proposto (opt): splittare in S5.3a (0016), S5.3b (0017), S5.3c (0018) — sforzo basso, tracciabilità migliore. O lasciare e accettare deviation con commento esplicito nel payload `Risks/notes`.

### 2.3 Observations (drift documentale, non blocca POST) — **5**

**OBS-1 — `docs/sprint-3-frontend.md` DoD §5 "10 issue chiusi" obsoleto**
- E2 ora ha 11 story (S2.11 aggiunta). Doc va aggiornata post-creazione issue su Plane.

**OBS-2 — `CLAUDE.md` drift su migration count + next prefix**
- Riga 28 "prossima 0009_" → corretta = 0006_. Riga 51 "8 migration files" → corretta = 5.
- Nessuna story copre fix. Aggiungere `[E2-S2.12] Update CLAUDE.md baseline (migrations + sprint state)` come housekeeping, oppure includere in S2.11 DoD.

**OBS-3 — `docs/agentos-context.md` §3 e §6 obsoleti**
- §3 elenca 8 migrations 0001-0008 (realtà 5); §6 dichiara `/daily-entries` (realtà = `/daily-inputs` + `/daily-production` split). Re-baseline post-E2.

**OBS-4 — `BLUEPRINT.md` v0.1 stale su schema `daily_entries` monolitico**
- Split `daily_input`/`daily_production` già applicato in DB. BLUEPRINT.md va rev a v0.2 post-Submission Gen 2025 (idealmente prima E3 inizia).

**OBS-5 — Action plan v3 §4 (Day 30 = 13 giu) vs blueprint §1 (Day 7 = 21 mag)**
- Action plan v3 ipotizzava 30gg estensione, blueprint riflette 5wd → 21 mag (decisione successiva DfT). PM ha già flaggato. Risoluzione = parte di D1 conferma Crown Oil. Da chiudere entro Day 1 EOD 5wd (15-mag-2026 23:59 UK).

**OBS-6 — E6-S6.8 Frontend Annex D worksheet sized XL, non splittato**
- PM raccomanda split S6.8a (form + state) + S6.8b (calc preview + submit). Accettabile lasciare unbundled fino a kickoff E6 se vincoli timing chiariti.

---

## 3. Decision blocks — D1-D10

| D | Domanda | Blocca | Earliest needed by |
|---|---|---|---|
| D1 | Decorrenza 5wd Crown Oil + deadline esatta UK time | E1 entire | **Day 1 EOD = 2026-05-15 23:59 UK** |
| D2 | Persistere litres_eu/litres_plus su daily_production? | E1-S1.1, opzionale mig 0007 | Day 1 EOD |
| D3 | Buyout strategy 2026 contingency | E5-S5.5 | Sprint 6 kickoff |
| D4 | ELT designato LCF su List of Feedstocks UK? (Q3 gap) | E3-S3.1 + tutto E4 | Sprint 4 kickoff (23 mag 2026) |
| D5 | Crown Oil contract basis (RTFC transfer vs supply) | E4-S4.1, S4.11 | Sprint 5 kickoff (13 giu 2026) |
| D6 | Verifier RTFO-recognised shortlist (Q5) | E5-S5.2, S5.6 | Sprint 6 kickoff (11 lug 2026) |
| D7 | ROS export formato XML vs CSV (DfT guidance) | E5-S5.4, S5.7 | Sprint 6 mid |
| D8 | Annex D approccio (worksheet replica vs reimpl) | E6-S6.1 | Sprint 7 kickoff (8 ago 2026) |
| D9 | Reminder channel: email solo / Slack / both | E5-S5.5 task | Sprint 6 kickoff |
| D10 | ANLA / Min.Ambiente path richieste OisteBio | E1-S1.14 | Day 2 (16 mag) |

---

## 4. Recommended actions (prima del POST a Plane)

1. **Tighten AC su E2-S2.11**: sostituire "tutti chiusi + smoke" con checklist 8-10 punti concreti, ciascuno con endpoint + risultato atteso. Owner: architect agent (low effort, ~10 min).
2. **Risolvere conditional 0007 (WARN-2)**: o aggiungere story stub `[E1-S1.6b] Migration 0007 persist litres` con `_conditional: D2=persist` nei sidecar, o documentare nel body S1.1 che orchestrator creerà la story addizionale post-decisione. Decidere prima del POST per evitare "stories fantasma" non tracciate.
3. **Add CLAUDE.md fix story (OBS-2)**: nuova story `[E2-S2.12] Update CLAUDE.md baseline + agentos-context.md staleness` size XS, Sprint 3. Oppure inserire come task esplicita dentro S2.11 DoD checklist.
4. **D1 conferma Crown Oil entro Day 1 EOD UK**: PM/architect devono produrre email/timestamp prima di Day 2 — altrimenti tutto E1 slitta e action-plan §4 (30gg) torna attivo come fallback. Tracciabilità in `docs/notes/decision-log-D1.md` consigliata.

Opzionale (post-POST, non blocca):
- 5. Split E5-S5.3 in 3 sub-stories (WARN-4) se traceability migration:story è valore alto per audit DfT.
- 6. Split E6-S6.8 in 8a/8b prima kickoff Sprint 7 (OBS-6).
- 7. Anticipare S5.1+S5.2 (anagrafica off_takers/verifiers) a Sprint 5 con seed admin-CLI; lasciare S5.6 UI in Sprint 6 (WARN-3).

---

## 5. Sign-off conditions checklist

Prima che orchestrator POST a Plane DFTEN:

- [ ] Action #1 eseguita — E2-S2.11 AC riscritti come checklist concreta
- [ ] Action #2 eseguita — strategia conditional 0007 documentata (story stub creata OPPURE body S1.1 aggiornato con "orchestrator-creates-on-decision")
- [ ] Action #3 eseguita — fix CLAUDE.md baseline coperto (S2.12 nuova story OR task in S2.11)
- [ ] Action #4 eseguita — D1 conferma Crown Oil acquisita o fallback action-plan v3 attivato esplicitamente
- [ ] WARN-3 + WARN-4 + OBS-6: o accettati esplicitamente con commento "deviation accepted" nei payload, o risolti con split
- [ ] Validation tecnica payload eseguita:
  - [ ] Tutti 68 payload con `state == 9c3f0600-ec31-40d5-9e46-e81a3442c089` (backlog DFTEN) — ✅ verificato
  - [ ] Tutti 68 `priority` ∈ {urgent, high, medium, low} — ✅ verificato (8/33/19/8)
  - [ ] Tutti `name` ≤ 80 caratteri — ✅ longest = 75 chars (E5-S5.3)
  - [ ] `_blocked_by` references resolvono a `_tmp_id` esistenti — ✅ verificato
  - [ ] Nessun secret/token/password in description_html — ✅ verificato (no `JWT_SECRET`, no API key, no `.env` content)
  - [ ] Counts coerenti: E1=18, E2=11, E3=9, E4=13, E5=9, E6=8 = 68 — ✅
  - [ ] Sprint distribution coerente: S3=29, S4=9, S5=13, S6=9, S7=8 = 68 — ✅
- [ ] CLAUDE.md hard rules non violati nei payload:
  - [ ] Nessun riferimento a hard-delete (tutte migrations supplier usano soft-delete `deleted_at`) — ✅ verificato S1.7
  - [ ] Nessun riferimento a write su `total_input_kg` (colonna GENERATED) — ✅ verificato
  - [ ] Pydantic v2 `model_dump()` rispettato — ✅ verificato
  - [ ] `REFRESH MATERIALIZED VIEW CONCURRENTLY` con AUTOCOMMIT mantenuto — ✅ esplicito S1.10

Se tutti i check sono ✅ o ☑️ con deviation accepted documentata: **GO for Plane POST**.

---

## 6. Note operative finali

- **Lingua payload:** italiano (coerente con blueprint + gap analysis). Plane UI multilingua, ok.
- **Backlog state UUID:** `9c3f0600-ec31-40d5-9e46-e81a3442c089` confermato unico su tutti 68.
- **HTML validity:** descrizioni usano solo `<h3>`, `<p>`, `<ul>`, `<li>`, `<strong>`, `&rarr;`, `&quot;` — Plane editor compatibile. Nessun tag form / script / iframe.
- **Cycles dependency graph:** verificato manualmente su 8 `urgent` + spine E1→E2→E3→E4→E5→E6 — nessun ciclo trovato.
- **Critical-path realism:** E1 7-giorni con 18 storie (8 urgent + 7 high + 3 medium/low) è aggressivo ma fattibile se Day 1 unblocks (D1+D2+WeasyPrint) chiudono entro EOD UK. Buffer Day 6-7 (Mer-Gio) per submission ROS + cover letter è sotto-stretto: raccomando shift di S1.16-S1.18 a Day 5 anziché Day 6.

— end reviewer pass v1 —
