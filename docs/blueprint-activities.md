# DFT — Blueprint Attività RTFO Roadmap

> Data: 2026-05-15
> Scope: 5wd Track A + Sprint 3 frontend + RTFO Phase 1-4
> Author: architect agent
> Source docs: `CLAUDE.md`, `docs/agentos-context.md`, `docs/rtfo-gap-analysis.it.md` v2, `docs/dft-action-plan-2026-05.md` v3, `docs/dft-5wd-activity-plan.md` v3, `docs/sprint-3-frontend.md`, `BLUEPRINT.md`

---

## 0. Stato attuale (baseline 2026-05-15)

Audit live del repo (non quanto dichiarato in CLAUDE.md, che è obsoleto su questo punto):

| Area | Cosa esiste | Cosa manca |
|---|---|---|
| Migrations Alembic | 5 applicate: `0001_schema`, `0002_seed`, `0003_mvs`, `0004_drop_stock_markers`, `0005_production_densities`. DB versione `0005`. Prossima `0006_`. | Tutto il resto. CLAUDE.md dichiara "8 migrations 0001-0008" — obsoleto, da rettificare. |
| Modelli ORM | `user`, `supplier`, `supplier_certificate`, `contract`, `certificate`, `daily_input`, `daily_production`, `audit_log` | `feedstock`, `ghg_calculation`, `off_taker`, `verifier`, `rtfc_batch`, `rtfc_event`, `obligation_period`, `collection_point`, `buyout_event` |
| Routers backend | `auth`, `anagrafica`, `daily_inputs`, `daily_production`, `reports`, `admin` (refresh-mvs + users + audit-log JSON) | `/reports/mass-balance/export` (PDF), `?format=csv` su `/admin/audit-log`, `/rtfc/*`, `/feedstocks`, `/ghg/*`, `/off-takers`, `/verifiers`, `/ros-export` |
| Schemas Pydantic | `audit_log`, `certificate`, `contract`, `daily_input`, `daily_production`, `reports`, `supplier`, `user` | Schemas per RTFO entities |
| Services | `audit`, `mv_refresh` | `pdf_renderer`, `hash_signer`, `ros_export`, `rtfc_ledger`, `ghg_annex_d` |
| Mass balance | `mv_mass_balance_daily` + `mv_mass_balance_monthly` con `eu_prod_litres` / `plus_prod_litres` / `total_prod_litres` via `product_densities` (EU 0.78, PLUS 0.856 — EAD 2026-05-13). Refresh AUTOCOMMIT. Closure Gen 2025: input 3.383.177 kg, eu_prod 760.828 kg / 975.420 L, plus 1.308.624 kg / 1.528.766 L, closure −10,05% (carry-over stock 339.865 kg). | Persistenza fisica `litres_eu`/`litres_plus` su `daily_production` (decisione aperta Day 1 5wd) |
| Audit | `audit_log` con `old_values` / `new_values` JSONB, IP, user_id, action. Endpoint `/admin/audit-log` JSON. | Export CSV (StreamingResponse) |
| Frontend `landing/` | Sprint 3 in flight: layout `app/(app)/` con sidebar, login con server actions, middleware JWT cookie, primitives shadcn (button/card/dialog/dropdown/table/select/badge/sheet/textarea), pagine `reports/mass-balance`, `reports/by-supplier`, `reports/closure-status`, `suppliers/[id]`, `suppliers/new`, `certificates`, `contracts`, `inputs`, `production`, `users`, `audit` | Verifica completezza S3-1..S3-10, fix gap, smoke test deploy oistebio.usenexos.com, snapshot bundle Day-7-ready |
| Deploy | Container `dft-back` + `dft-project_db_1` healthy. Caddy 2 reverse proxy. PM2 + nginx per landing su Hetzner (oistebio.usenexos.com). | Deploy backend produzione UK-time consciousness; persisted snapshot script |
| PDF / hash | **Inesistente** — zero `weasyprint`/`reportlab`/`hashlib` nel backend. | Endpoint + service + template Jinja, hash side-car SHA-256 |
| RTFO entity model | **Inesistente.** | Tutto Phase 1-4 |

Conflitti trovati tra source docs:
1. `CLAUDE.md` riga 28 dichiara prossima migration `0009_`. Realtà = `0006_`. Da correggere in CLAUDE.md a sprint successivo.
2. `CLAUDE.md` riga 51 dichiara "8 migration files". Realtà = 5. Da correggere.
3. `agentos-context.md` §3 elenca 8 migrazioni (0001-0008) con nomi storici. Realtà = 5 migrazioni con nomi diversi. Doc obsoleto, da rifare.
4. `agentos-context.md` §6 dichiara endpoint `/daily-entries`; realtà = `/daily-inputs` + `/daily-production` (split deliberato). Doc obsoleto.
5. `BLUEPRINT.md` §3 mostra schema `daily_entries` monolitico; in realtà il refactor ha già splittato `daily_input` + `daily_production`. BLUEPRINT.md va rivisto post-RTFC submission Gen 2025.

---

## 1. Epic structure

| Epic | Titolo | Window | Driver |
|---|---|---|---|
| E1 | `e1-5wd-track-a-submission-jan2025` | 15-21 mag 2026 | Submission DfT RTFO-310125 |
| E2 | `e2-sprint3-frontend-completion` | 15-31 mag 2026 | 10 storie già in `docs/sprint-3-frontend.md`, mai entrate in Plane |
| E3 | `e3-rtfo-phase1-prep-readonly` | giu-lug 2026 | Gap §5 Fase 1 — readiness read-only |
| E4 | `e4-rtfo-phase2-ledger` | post Crown Oil contract | Gap §5 Fase 2 — RTFC ledger |
| E5 | `e5-rtfo-phase3-reporting-automation` | dopo E4 | Gap §5 Fase 3 — ROS export + reminders + verifier bundle |
| E6 | `e6-rtfo-phase4-ghg-annex-d-automation` | dopo E5 | Gap §5 Fase 4 — Annex D in codice + Carbon Calculator |

---

## 2. Per ogni Epic

### E1 — 5wd Track A submission bundle Gennaio 2025

- **Goal:** Sottomettere su ROS entro Gio 21 mag 2026 23:59 UK il bundle singolo coerente RTFO-310125 (Gennaio 2025), seguendo timeline 7-giorni `dft-5wd-activity-plan.md` v3 §3.
- **Scope IN:** PDF audit-grade mass-balance Gen 2025; production conversion log kg→litri; audit log CSV; supply chain diagram; Annex D stock 339.865 kg; bonifica fornitori limitata a Gen 2025; cover letter + evidence index; snapshot DB crittografico; submission ROS; notifica formale DfT.
- **Scope OUT:** PoS ISCC retroattivo (gap dichiarato), legalizzazione consolare (gap dichiarato), pre-audit verifier indipendente (offerto in lettera), bundle Feb-Ago 2025, qualsiasi sviluppo RTFO Phase 2-4.
- **Dependencies:** Conferma scritta Crown Oil su decorrenza 5wd, scope, deadline esatta (item §1 di 5wd plan). Copie ANLA/Min.Ambiente da OisteBio. Richiesta PoS retroattivo OisteBio→certifier Colombia entro Day 1.
- **Migration(s) needed:** `0006_supplier_rectification_jan2025.py` (Day 2 sabato — riclassificazione soft-delete fornitori Gen 2025 con audit_log preservato); opzionale `0007_persist_production_litres.py` se decisione Day 1 = persistere `litres_eu`/`litres_plus` come colonne fisiche su `daily_production` per audit immutabile.
- **Data model changes:** Nessuna nuova entità RTFO. Sole modifiche tabella `suppliers` (soft-delete + note) e opzionalmente `daily_production` (colonne litres persistite).
- **API endpoints needed:**
  - `GET /reports/mass-balance/export?month=2025-01&format=pdf` → PDF + side-car `.sha256`
  - `GET /admin/audit-log?since=YYYY-MM-DD&until=YYYY-MM-DD&format=csv` → StreamingResponse text/csv UTF-8 BOM
- **Frontend changes:** Nessuna richiesta — bundle prodotto via API + script. Eventuale link "Esporta bundle Gennaio 2025" in `/app/reports/mass-balance` deferred.
- **Risk flags:** dipendenze sistema WeasyPrint (cairo/pango/gdk-pixbuf) in container `dft-back`; team weekend availability; certifier ISCC silence.

**Stories:**

- **S1.1 — Verifica decisione persistenza `litres` su `daily_production`** (S, Day 1)
  - **AC:** Decisione tracciata in repo (commento commit o `docs/notes/`); se "persistere" → migration `0007` pronta; se "MV-only" → nessuna migration, MV ricomputate ad ogni refresh.
  - **Tasks:** T1 verificare presenza `eu_prod_litres`/`plus_prod_litres` in `mv_mass_balance_daily` via `\d+ mv_mass_balance_daily`; T2 audit stakeholder DfT su accettabilità "computed view" vs "physical column" per ispezione; T3 documentare scelta.
  - **Complexity:** S — **Risk:** basso.

- **S1.2 — Setup WeasyPrint runtime + template base** (M, Day 1)
  - **AC:** `pip install weasyprint==<latest stable>` aggiunto a `backend/requirements.txt`; `apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf2.0-0` aggiunto a `backend/Dockerfile`; `docker compose build backend` succede; smoke test `python -c "from weasyprint import HTML; HTML(string='<h1>ok</h1>').write_pdf('/tmp/x.pdf')"` esegue dentro container.
  - **Tasks:** T1 patch Dockerfile; T2 patch requirements; T3 verificare versione python-jose/pydantic non rotta; T4 fallback documentato `reportlab` se WeasyPrint fallisce setup.
  - **Risk flags:** dipendenze sistema mancanti.

- **S1.3 — Service `pdf_renderer` + hash side-car** (M, Day 1)
  - **AC:** `backend/app/services/pdf_renderer.py` con funzione `render_pdf(template_name, context) -> bytes` e `hash_pdf(pdf_bytes) -> str` (SHA-256 hex digest); template Jinja in `backend/app/templates/reports/mass_balance.html` con header firma, footer hash, paginazione mese, tabella giorni + aggregato mensile + closing stock.
  - **Tasks:** T1 creare struttura `templates/reports/`; T2 design template HTML con CSS print-friendly (page-break, header/footer); T3 helper `hash_pdf` con `hashlib.sha256`; T4 unit test su sample.
  - **Risk flags:** template scope creep.

- **S1.4 — Endpoint `/reports/mass-balance/export` PDF** (M, Day 1-2)
  - **AC:** `GET /reports/mass-balance/export?month=YYYY-MM&format=pdf` ritorna `Response(media_type="application/pdf")` + header `X-Content-SHA256: <hex>`; richiede Bearer; usa MV mensile + giornaliera; range valida (formato YYYY-MM); errore 400 se mese non valido.
  - **Tasks:** T1 nuovo handler in `backend/app/routers/reports.py`; T2 query MV per `mv_mass_balance_daily` filtrata + MV monthly aggregata; T3 chiamata `pdf_renderer.render_pdf` + `hash_pdf`; T4 audit log entry "REPORT_EXPORT" su `audit_log`; T5 test smoke.
  - **Files:** `backend/app/routers/reports.py`, `backend/app/services/pdf_renderer.py`.

- **S1.5 — Generazione Annex A v1 Gennaio 2025** (S, Day 1)
  - **AC:** File `bundle_RTFO-310125/02_mass_balance_january_2025_v1.pdf` + `.sha256` generato via endpoint S1.4; closure −10,05% leggibile + carry-over 339.865 kg dichiarato in footnote.
  - **Tasks:** T1 chiamata curl autenticata; T2 verifica hash; T3 review visivo team ingest.

- **S1.6 — Hardening template + Annex A v2** (S, Day 2)
  - **AC:** Template stabile, paginazione mese OK, header firma OisteBio, footer hash + page n/N, font deterministico; rigenera `v2` + hash; review OisteBio.
  - **Tasks:** T1 fix bug visivi v1; T2 commit template `templates/reports/mass_balance.html`; T3 rigenera bundle file.

- **S1.7 — Migration `0006_supplier_rectification_jan2025`** (M, Day 2)
  - **AC:** Riclassificazione fornitori Gen 2025 applicata via UPDATE (mai DELETE); soft-delete sui supplier_id mal classificati con `deleted_at` + note "DfT investigation reclassification 2026-05"; ogni riga `daily_input` riallineata logga in `audit_log` con `old_values`/`new_values`; query closure mass-balance pre/post = delta ≤ 0.01% kg (no underdeclared input).
  - **Tasks:** T1 mapping definitivo fornitori (Litoplas/Biowaste/Esenttia) — atteso da OisteBio; T2 file `backend/alembic/versions/0006_supplier_rectification_jan2025.py`; T3 transaction wrap che popola `audit_log` per ogni UPDATE; T4 dry-run su DB locale + diff input_kg/day pre/post; T5 apply prod con backup.
  - **Risk flags:** delta closure > 0.01% → rollback immediato.

- **S1.8 — Annex D closing stock 339.865 kg PDF** (S, Day 2)
  - **AC:** PDF `07_stock_carryover_explanation.pdf` con composizione 17 K-only rows JANUARY2025 (righe 48, 78, 94, 108, 138, 194, 223, 228-233, 267, 283, 314, 330), dichiarazione "fisicamente disponibile in facility OisteBio", riferimento record interno; firma OisteBio scansionata; hash SHA-256 side-car.
  - **Tasks:** T1 template Jinja dedicato in `backend/app/templates/reports/stock_carryover.html`; T2 dati statici da memoria progetto; T3 rendering via stessa `pdf_renderer`.

- **S1.9 — Endpoint CSV `/admin/audit-log?format=csv`** (S, Day 3)
  - **AC:** Stesso endpoint accetta param `format=csv` (default `json`); con `format=csv` ritorna `StreamingResponse(media_type="text/csv")` con BOM UTF-8; colonne fisse: `id,timestamp,user_email,action,table_name,record_id,old_values,new_values,ip_address`; filtri `since`/`until` rispettati; richiede `AdminUser`.
  - **Tasks:** T1 patch `backend/app/routers/admin.py` ramo CSV; T2 generator function streamato; T3 escape CSV (RFC4180) per JSONB old/new_values; T4 smoke test export Gen 2025; T5 verifica Excel apre con accenti corretti.
  - **Files:** `backend/app/routers/admin.py`.

- **S1.10 — Production conversion log Gen 2025 PDF** (S, Day 3)
  - **AC:** PDF `05_production_conversion_logs_january_2025.pdf` che mostra per ogni giorno Gen 2025: `eu_prod_kg`, `plus_prod_kg`, lookup densities EU 0.78 / PLUS 0.856, formula `litres = kg / density`, totale mensile in litri; firma OisteBio + hash side-car.
  - **Tasks:** T1 template `templates/reports/production_conversion.html`; T2 query MV daily; T3 rendering pipeline.

- **S1.11 — Supply chain diagram PDF** (S, Day 3)
  - **AC:** PDF `01_supply_chain_diagram.pdf` con quattro layer (origin → collecting point Litoplas/Biowaste/Esenttia → OisteBio Girardot → Crown Oil UK); diagramma vettoriale (Graphviz / mermaid render o disegno statico SVG); cert ISCC overlay come placeholder dove ancora non disponibili (gap dichiarato).
  - **Tasks:** T1 scegliere tool (Graphviz CLI in container backend è opzione semplice); T2 input dati da supplier mapping post-S1.7; T3 render statico una-tantum, commit nel bundle.

- **S1.12 — Cover letter + evidence index PDF** (M, Day 4-6)
  - **AC:** `00_cover_letter.pdf` firmato Crown Oil con sezione "Outstanding items" (3 gap residui da §5 di 5wd-plan); `09_evidence_index.pdf` cross-reference tabella docs ↔ punti rigetto DfT.
  - **Tasks:** T1 v0 draft Day 1 (Crown Oil); T2 v1 Day 4 review legale; T3 v2 Day 5 incorporare evidence definitive; T4 FINAL Day 6 firmato; T5 evidence index renderizzato via pdf_renderer + dati statici.

- **S1.13 — `03_iscc_pos_status.pdf`** (S, Day 4)
  - **AC:** PDF documenta richiesta retroattiva inviata Day 1 + risposta certifier (se ricevuta entro Day 6) + impegno consegna post-acceptance.
  - **Tasks:** T1 raccogliere timestamp email; T2 template Jinja; T3 firma OisteBio.

- **S1.14 — `04_feedstock_provider_authorisations/` copie semplici + nota stato** (S, Day 3-4)
  - **AC:** Cartella con PDF per Litoplas/Biowaste/Esenttia (copie ANLA/Min.Ambiente non legalizzate) + `_status_legalisation.pdf` con ETA legalizzazione consolare.
  - **Tasks:** T1 OisteBio fornisce copie; T2 nota stato legalizzazione.

- **S1.15 — Pre-audit interno bundle Day 4** (M, Day 4)
  - **AC:** Checklist firmata team ingest + OisteBio + Crown Oil con verifica completezza Annex A/B/C/D + production log + audit CSV; gap emersi listati per Day 5 fix.
  - **Tasks:** T1 checklist template; T2 walk-through bundle; T3 lista azioni Day 5.

- **S1.16 — Snapshot crittografico DB Day 5 + Day 6** (S, Day 5/6)
  - **AC:** `db_snapshot_2026-05-19.sql.gz` + `.sha256` (Day 5 preliminare); `db_snapshot_2026-05-20.sql.gz` + `.sha256` (Day 6 FINAL); comando `pg_dump dft | gzip | tee snapshot.sql.gz | sha256sum > snapshot.sha256`.
  - **Tasks:** T1 script `scripts/snapshot_db.sh` con timestamp + hash; T2 esecuzione dentro container `dft-back`; T3 storage offline.

- **S1.17 — Audit interno bundle Day 6 + Annex A FINAL** (M, Day 6)
  - **AC:** Cross-reference ogni kg Gennaio in mass-balance ↔ daily_input ↔ supplier ↔ PoS o gap dichiarato; checklist firmata; Annex A rigenerato come `02_mass_balance_january_2025_FINAL.pdf` con hash FINAL elencato in evidence index.
  - **Tasks:** T1 walkthrough Crown Oil + OisteBio + team ingest; T2 fix gap; T3 rigenera Annex A; T4 update evidence index con hash definitivo; T5 cover letter cita hash manifest.

- **S1.18 — Submission ROS Day 7 + notifica formale DfT** (S, Day 7)
  - **AC:** Verifica integrità bundle (file presenti, hash verificati, dimensioni); telefonata cortesia DfT contact (mattina); upload su ROS (pomeriggio); email notifica formale al contact DfT con lista allegati + hash file principale (EOD).
  - **Tasks:** T1 checklist integrità; T2 chiamata; T3 upload; T4 email.
  - **Risk flags:** Slittamento Day 6 → buffer mattina Day 7; slittamento Day 7 = pathway 2025 Gen chiusa.

**Cross-ref:** S1.1-S1.18 implementano timeline Day 1-7 di `dft-5wd-activity-plan.md` v3 §3; bundle structure conforme a §8 di `dft-action-plan-2026-05.md` v3 con modifiche §4 di 5wd-plan.

---

### E2 — Sprint 3 frontend completion

- **Goal:** Portare a Done in Plane le 10 storie già draftate in `docs/sprint-3-frontend.md` (DFTEN-72..81). Codebase landing/ è in flight; verificare allineamento spec ↔ realtà e chiudere gap residui.
- **Scope IN:** Tutte le 10 storie S3-1..S3-10 (vedi §3 di sprint-3-frontend.md), Definition of Done §5 di quel doc, deploy oistebio.usenexos.com.
- **Scope OUT:** CRUD anagrafiche complete (Sprint 4+), data entry forms, PDF generation client-side, audit log viewer admin, i18n switcher, dark mode, mobile responsive avanzato, E2E Playwright.
- **Dependencies:** Backend FastAPI raggiungibile su `BACKEND_URL` (dev `localhost:18000`, prod `127.0.0.1:8000`); JWT_SECRET allineato backend↔frontend; MV popolate (refresh-mvs); seed admin `admin@dft-project.com`.
- **Migration(s) needed:** Nessuna — Sprint 3 è puro frontend integration.
- **Data model changes:** Nessuna.
- **API endpoints needed:** Tutti già esistenti (`/auth/login`, `/auth/me`, `/reports/mass-balance/daily|monthly`, `/reports/by-supplier`, `/reports/closure-status`, `/suppliers`, `/contracts`, `/certificates`, `/daily-inputs`, `/daily-production`).
- **Frontend changes:** Routes definite in §1 di sprint-3-frontend.md.

**Stories:** (mapping 1:1 da `docs/sprint-3-frontend.md` §3 — l'AC è riassunto; spec autoritativa rimane il doc sprint-3-frontend.md.)

- **S2.1 — Setup shadcn/ui + base UI primitives** (M)
  - **AC:** componenti base in `landing/src/components/ui/` (button, input, label, form, card, table, dialog, dropdown-menu, select, toast, badge); design tokens (`var(--bg)`, `var(--ink)`) preservati.
  - **State live:** già in flight — verificare presenza tutti i primitives, integrare quelli mancanti (`form`, `toast` da check).

- **S2.2 — API client lib + tipi backend** (M)
  - **AC:** `landing/src/lib/api.ts` typed fetch wrapper; tipi generati da `/openapi.json` via `openapi-typescript`; `apiGet/apiPost/apiPatch/apiDelete`; `ApiError(status, code, detail)` tipizzato; cookie reading server-only.
  - **Tasks:** T1 verifica `lib/api.ts` esiste; T2 verifica generazione tipi; T3 helper auth injection.

- **S2.3 — Auth flow login/logout** (M)
  - **AC:** `/login` con server actions (`loginAction`/`logoutAction` in `src/lib/auth.ts`); cookie `dft_session` httpOnly+Secure(prod)+SameSite=Lax, Max-Age 8h; redirect `/app` su login, `/` su logout.
  - **State live:** `landing/src/app/login/` esiste con `login-form.tsx` + `page.tsx`. Verificare conformità AC.

- **S2.4 — Middleware route protection** (M)
  - **AC:** `landing/src/middleware.ts` matcher `/app/:path*`, JWT verify via `jose`, redirect `/login?next=${pathname}` se mancante/invalido/scaduto; cookie cleared se scaduto.
  - **State live:** `landing/src/middleware.ts` esiste. Verificare matcher + jose verify + path next.

- **S2.5 — Dashboard layout shell** (M)
  - **AC:** `(app)/layout.tsx` sidebar fissa + topbar; nav Dashboard/Reports/Anagrafiche; sidebar collassabile mobile (Radix sheet); user dropdown + logout.
  - **State live:** `landing/src/app/app/layout.tsx` esiste — verificare conformità.

- **S2.6 — Dashboard home KPI cards** (M)
  - **AC:** `(app)/page.tsx` server component; 4 KPI (Input 30g, Output 30g, Closure %, Alert count); sparkline Recharts; render <500ms; thousand separator IT.
  - **State live:** `landing/src/app/app/page.tsx` esiste — verificare KPI cards + sparkline.

- **S2.7 — Report mass balance daily/monthly** (L)
  - **AC:** Tab daily/monthly; date range picker (default 30g); TanStack Table v8 con sorting + pagination 50/pagina; export CSV UTF-8 BOM.
  - **State live:** `landing/src/app/app/reports/mass-balance/page.tsx` + helpers (`kpi-tile-tooltip.tsx`, `month-quick-picker.tsx`, `month-utils.ts`) esistono — verificare AC.

- **S2.8 — Report by-supplier (chart + table)** (M)
  - **AC:** Pie chart Recharts top-7 + "Altri"; tabella ranking; click pie → highlight tabella; date range picker.
  - **State live:** `landing/src/app/app/reports/by-supplier/page.tsx` esiste.

- **S2.9 — Report closure-status (semaforo)** (M)
  - **AC:** Tabella con `bucket` come Badge colorato (ok=green/warn=yellow/alert=red/no_input/no_output=gray); label IT; filtro per bucket.
  - **State live:** `landing/src/app/app/reports/closure-status/page.tsx` esiste.

- **S2.10 — Anagrafiche read-only viewer** (M)
  - **AC:** `suppliers`, `certificates`, `contracts` listate via TanStack Table + search; detail view read-only su `/app/suppliers/[id]`.
  - **State live:** `landing/src/app/app/suppliers/` (con `[id]`, `_components`, `new`, `page.tsx`), `certificates/`, `contracts/` esistono — verificare spec compliance.

- **S2.11 — Sprint 3 DoD verification + deploy smoke test** (M, nuova)
  - **AC:** DoD §5 sprint-3-frontend.md verificato item-per-item; `npm run build` zero errori; `npm run lint` zero warnings; login E2E manuale; deploy locale port 3020 OK; deploy prod oistebio.usenexos.com OK; commit CLAUDE.md update.

**Risk flags:** JWT_SECRET disallineato dev↔prod; bundle size esplosione con recharts+tanstack; hydration mismatch SSR React Query.

---

### E3 — RTFO Phase 1: Prep readiness (read-only)

- **Goal:** Implementare le fondamenta dati RTFO senza implementare RTFC ledger. Risponde a `rtfo-gap-analysis.it.md` §5 Fase 1: feedstocks + GHG storage + scheme enum. Sistema resta usabile per ISCC EU; nuove tabelle popolabili manualmente.
- **Scope IN:** Tabella `feedstocks` con seed RTFO List of Feedstocks; FK `daily_inputs.feedstock_id`; tabella `ghg_calculations` con upload manuale CI; enum `Certificate.scheme` allineato lista DfT-recognised.
- **Scope OUT:** Calcolo automatico Annex D, RTFC ledger, ROS export, off-takers, verifiers, reminders, buyout.
- **Dependencies:** Lista feedstock RTFO ufficiale (fetch dal sito DfT); decisione enum values per `Certificate.scheme` (lista DfT recognised voluntary schemes).
- **Migration(s) needed:**
  - `0008_feedstocks_table.py` — crea `feedstocks(id, code, name, rtfo_class enum, double_counting_eligible bool, lcf_designation_status enum, designated_at date, notes, created_at, deleted_at)`; FK `daily_inputs.feedstock_id` nullable; seed iniziale ELT/RCF.
  - `0009_ghg_calculations_table.py` — crea `ghg_calculations(id, daily_production_id FK, methodology enum {red_ii_default, red_ii_actual, annex_d_counterfactual}, methodology_version varchar, ci_cultivation gCO2eq/MJ, ci_processing, ci_transport, ci_total, baseline_fossil_gCO2eq_MJ default 94, ghg_saving_pct, threshold_met bool, source_doc_url, uploaded_by FK users, uploaded_at, deleted_at)`; FK `daily_production.ghg_calculation_id` nullable.
  - `0010_certificate_scheme_enum.py` — converte `Certificate.scheme` VARCHAR → enum `certificate_scheme` ∈ `{ISCC_EU, ISCC_PLUS, REDcert, REDcert_EU, RSB_EU_RED, RSB_Global, KZR_INiG, _2BSvs, Bonsucro, ...}`; migration data-preserving (UPDATE prima di ALTER).
- **Data model changes:**
  - Nuove tabelle: `feedstocks`, `ghg_calculations`.
  - Nuovi enum PostgreSQL: `rtfo_class`, `lcf_designation_status`, `ghg_methodology`, `certificate_scheme`.
  - Nuove FK: `daily_inputs.feedstock_id`, `daily_production.ghg_calculation_id`.
- **API endpoints needed:**
  - `GET|POST|PATCH /feedstocks` (CRUD admin)
  - `GET /feedstocks/{id}`
  - `POST /ghg-calculations` (upload manuale, multipart o JSON)
  - `GET /ghg-calculations?daily_production_id=` o `?period=YYYY-MM`
  - `GET /ghg-calculations/{id}`
  - Validazione: blocca applicazione RTFC se `threshold_met = false`.
- **Frontend changes:**
  - `/app/feedstocks/` (admin read+CRUD)
  - `/app/feedstocks/[id]`
  - `/app/ghg/` (upload + visualizza)
  - Sidebar nav aggiunge gruppo "RTFO" con sotto-link Feedstocks + GHG (visibile solo `admin`/`certifier`)

**Stories:**

- **S3.1 — Fetch RTFO List of Feedstocks ufficiale + decidere seed** (S)
  - **AC:** Documento `docs/rtfo-feedstock-list.md` con CSV inline (code, name, rtfo_class, double_counting_eligible, source URL DfT, fetch date); ELT presente con `rtfo_class=rcf` + `lcf_designation_status=pending` (gap §7 Q3).
  - **Tasks:** T1 WebFetch lista DfT; T2 normalizzare CSV; T3 commit doc.

- **S3.2 — Migration 0008 feedstocks** (M)
  - **AC:** Schema feedstocks creato; FK su daily_inputs nullable; seed da CSV S3.1; tutti i daily_input esistenti restano `feedstock_id NULL` (back-population in S3.3).
  - **Files:** `backend/alembic/versions/0008_feedstocks.py`, `backend/app/models/feedstock.py`, `backend/app/schemas/feedstock.py`.

- **S3.3 — Back-population `daily_inputs.feedstock_id` ELT** (S)
  - **AC:** Script `scripts/backfill_feedstock_elt.py` che UPDATE `daily_inputs.feedstock_id = (SELECT id FROM feedstocks WHERE code='ELT')` per tutte le righe esistenti; audit_log entries; rollback safe.
  - **Risk flags:** scope corrente è ELT-only, banale; in futuro feedstock biogenico richiede logica per riga.

- **S3.4 — Router `/feedstocks` CRUD** (M)
  - **AC:** CRUD standard pattern come `routers/anagrafica.py`; `admin` only per POST/PATCH; `viewer` può GET; audit_log integration.
  - **Files:** `backend/app/routers/feedstocks.py`, `backend/app/main.py` (include).

- **S3.5 — Migration 0009 ghg_calculations** (M)
  - **AC:** Schema creato; FK su daily_production nullable; enum `ghg_methodology` definito; constraint check `baseline_fossil_gCO2eq_MJ > 0`; constraint `ghg_saving_pct = (baseline - ci_total)/baseline * 100`.
  - **Files:** `backend/alembic/versions/0009_ghg_calculations.py`, `backend/app/models/ghg_calculation.py`, `backend/app/schemas/ghg_calculation.py`.

- **S3.6 — Router `/ghg-calculations` upload manuale** (M)
  - **AC:** `POST /ghg-calculations` accetta JSON body (no upload file in Fase 1, solo metadata + values); compute `ghg_saving_pct` server-side; flag `threshold_met = ghg_saving_pct >= 65`; ritorna 422 se sotto soglia con warning (non blocca insert).
  - **Files:** `backend/app/routers/ghg_calculations.py`.

- **S3.7 — Migration 0010 certificate scheme enum** (M)
  - **AC:** Data-preserving migration: UPDATE valori esistenti `'ISCC EU' → 'ISCC_EU'`, `'ISCC' → 'ISCC_EU'`, etc; ALTER COLUMN type su enum; rollback path documentato; nessuna riga persa.
  - **Risk flags:** migrazione su tabella già popolata in prod, eseguire backup pre-apply.

- **S3.8 — Frontend `/app/feedstocks/` list + detail** (M)
  - **AC:** Tabella TanStack feedstocks; filtro per `rtfo_class`; detail view `/app/feedstocks/[id]` mostra link a daily_inputs collegati.

- **S3.9 — Frontend `/app/ghg/` upload + view** (L)
  - **AC:** Form upload (`react-hook-form` + `zod`) con campi CI per stadio + auto-compute saving %; tabella GHG calculations recenti; warning visivo se `threshold_met=false`.

**Risk flags:** Lista RTFO feedstock può cambiare annualmente — versionare seed; rcf designation per ELT è ancora pending (Q3 gap §7).

---

### E4 — RTFO Phase 2: RTFC ledger (post Crown Oil engagement)

- **Goal:** Implementare ledger negoziabile di RTFC + dRTFC quando Crown Oil firma contratto e diventa applicant ufficiale. Risponde a `rtfo-gap-analysis.it.md` §5 Fase 2 + §3.3 + §3.4.
- **Scope IN:** `off_takers`, `verifiers`, `obligation_periods`, `rtfc_batches`, `rtfc_events`, view `rtfc_balance`, carry-over 25% annuale singolo, link batch ↔ ghg_calculation ↔ daily_production.
- **Scope OUT:** Export ROS (E5), buyout cash ledger (E5), reminder 15-set (E5), Annex D code (E6).
- **Dependencies:** Crown Oil firma contratto + decisione Q4 §7 gap (fisica segregata vs mass-balance); designazione LCF ELT (Q3); identificazione verifier RTFO-recognised (Q5).
- **Migration(s) needed:**
  - `0011_off_takers.py` — `off_takers(id, name, uk_obligated bool, hmrc_excise_id, country, address, contract_basis enum {physical_segregated, mass_balance}, active, created_at, deleted_at)`; seed Crown Oil UK.
  - `0012_verifiers.py` — `verifiers(id, name, rtfo_recognised bool, recognition_source_url, recognition_date, country, accreditation_id, active, deleted_at)`.
  - `0013_obligation_periods.py` — `obligation_periods(year smallint PK, start_date date, end_date date, submission_deadline date default 15-Sep-Y+1, main_obligation_pct, dev_subtarget_pct, buyout_main_gbp default 0.50, buyout_dev_gbp default 0.80, locked bool)`.
  - `0014_rtfc_batches.py` — `rtfc_batches(id, obligation_period_year FK, class enum {general, relevant_crop, drtfc_double, drtfc_rcf, drtfc_rfnbo}, daily_production_id FK, ghg_calculation_id FK, off_taker_id FK, verifier_id FK, litres_eligible, drtfc_qty, rtfc_qty, status enum {draft, verified, awarded, redeemed, sold, cancelled}, evidence_bundle_url, created_at, deleted_at)`.
  - `0015_rtfc_events.py` — `rtfc_events(id, batch_id FK, event_type enum {awarded, redeemed, sold, bought, carried_over, bought_out, cancelled}, qty, counterparty_off_taker_id FK nullable, counterparty_external_name, price_per_cert_gbp, event_date, user_id FK, audit_ref_id FK audit_log, created_at)`.
- **Data model changes:** 5 nuove tabelle + 5 nuovi enum (`contract_basis`, `rtfc_class`, `rtfc_status`, `rtfc_event_type`).
- **API endpoints needed:**
  - `GET|POST|PATCH /off-takers`
  - `GET|POST|PATCH /verifiers`
  - `GET /obligation-periods` (read-only seed admin)
  - `GET|POST /rtfc-batches`; `PATCH /rtfc-batches/{id}` (status transitions)
  - `POST /rtfc-events` (append-only, mai PATCH/DELETE)
  - `GET /rtfc-balance?year=YYYY&class=...` (view aggregata)
  - `POST /rtfc-batches/{id}/carry-over?to_year=` (max 25% del balance)
- **Frontend changes:**
  - `/app/rtfo/off-takers/`
  - `/app/rtfo/verifiers/`
  - `/app/rtfo/batches/` (con [id] detail)
  - `/app/rtfo/events/` (timeline)
  - `/app/rtfo/balance/` (per obligation period)

**Stories:**

- **S4.1 — Migration 0011 off_takers + Crown Oil seed** (M)
  - **AC:** Tabella creata, Crown Oil seeded con `uk_obligated=true`, `contract_basis` come `mass_balance` o `physical_segregated` per Q4 gap §7.
  - **Risk flags:** contract_basis dipende da decisione cliente.

- **S4.2 — Migration 0012 verifiers** (M)
  - **AC:** Schema creato; nessun seed iniziale (Q5 ancora aperto).

- **S4.3 — Migration 0013 obligation_periods + seed 2025+2026** (S)
  - **AC:** Seed `2025` (main 14,054%, dev 1,619%, buyout main £0,50, dev £0,80, deadline 15-set-2026) + `2026` (valori 2026 da pubblicazione DfT, placeholder fino a fetch).

- **S4.4 — Migration 0014 rtfc_batches** (L)
  - **AC:** Schema con tutti FK + enum; check constraint `litres_eligible > 0`; check `drtfc_qty + rtfc_qty > 0`.

- **S4.5 — Migration 0015 rtfc_events** (M)
  - **AC:** Schema append-only (no soft-delete, no PATCH; cancellazione via event_type `cancelled`); FK audit_log per ogni evento.

- **S4.6 — Router `/off-takers` CRUD** (M)
- **S4.7 — Router `/verifiers` CRUD** (M)
- **S4.8 — Router `/rtfc-batches` con state machine** (L)
  - **AC:** State transitions: `draft → verified → awarded → (redeemed | sold | cancelled)`; transizioni invalid → 409; ogni transizione logga evento + audit_log.

- **S4.9 — Router `/rtfc-events` append-only** (M)
  - **AC:** POST only; GET con filtri; pagination.

- **S4.10 — View `rtfc_balance` per obligation period** (M)
  - **AC:** Materialized view o computed query; aggrega per `year` + `class`; mostra `awarded - redeemed - sold + bought - bought_out + carried_in - carried_out`.

- **S4.11 — Carry-over 25% annuale singolo endpoint** (M)
  - **AC:** `POST /rtfc-batches/{id}/carry-over` valida `qty ≤ 0.25 * available_balance(class, year)` e che `to_year = year+1`; rifiuta double carry-over (no carry-over di carry-over).

- **S4.12 — Frontend `/app/rtfo/*` shell** (L)
  - **AC:** Sidebar nav "RTFO Ledger" gruppo con sotto-link batches/events/balance/off-takers/verifiers; visibili admin/operator/certifier.

- **S4.13 — Frontend batch detail + state transitions** (L)
  - **AC:** Detail page batch mostra eventi cronologici, stato corrente, bottoni transizione (admin only).

**Risk flags:** Q3/Q4/Q5 gap §7 sbloccano completamente; senza Crown Oil contract → epic deferito.

---

### E5 — RTFO Phase 3: Reporting + automazione

- **Goal:** Automatizzare submission ROS + reminders + bundle verificatore. Risponde a Fase 3 (gap §5).
- **Scope IN:** View `rtfo_export` ROS-compatibile + endpoint export idempotente; scheduler reminder 15-set; buyout cash ledger; bundle PDF verificatore.
- **Scope OUT:** Annex D in codice (E6); integrazione DfT Carbon Calculator (E6).
- **Dependencies:** Schema ROS pubblicato (fetch separato — gap §7 Q "ROS schema fetch"); E4 completato; off-taker contract decision Q4.
- **Migration(s) needed:**
  - `0016_buyout_events.py` — `buyout_events(id, obligation_period_year FK, class enum, qty_cert, price_per_cert_gbp, total_paid_gbp, paid_date, reference, user_id FK, audit_ref_id, created_at)`.
  - `0017_reminders.py` — `reminders(id, period_year FK, type enum {submission_deadline, interim_status, buyout_decision}, due_date, sent_at, recipient_email, status enum {pending, sent, acknowledged, dismissed}, created_at)`.
  - `0018_ros_exports.py` — `ros_exports(id, period_year, exported_at, file_path, sha256, status enum {draft, submitted, accepted, rejected}, dft_response_url, user_id FK)`.
- **Data model changes:** 3 nuove tabelle + 2 enum.
- **API endpoints needed:**
  - `GET /ros-export?year=YYYY&format=json|csv|xml` (idempotent, versioned in audit_log)
  - `POST /ros-export?year=YYYY` (mark as submitted)
  - `POST /buyout-events`
  - `GET /buyout-events?year=`
  - `GET /reminders` + `POST /reminders/{id}/acknowledge`
  - `POST /reports/verifier-bundle?year=YYYY&class=` → ZIP con PDF bundle + manifest hash
- **Frontend changes:**
  - `/app/rtfo/ros-export/`
  - `/app/rtfo/buyout/`
  - `/app/rtfo/reminders/`
  - `/app/rtfo/verifier-bundle/`

**Stories:**

- **S5.1 — Fetch ROS schema (DfT API o spec scaricabile)** (M)
  - **AC:** `docs/ros-schema.md` con definizione campi attesi; mapping `rtfc_batches` + `rtfc_events` → ROS fields.
  - **Risk flags:** schema può cambiare anno su anno.

- **S5.2 — View + endpoint `/ros-export`** (L)
  - **AC:** Query che produce esattamente formato ROS; idempotente (stessa risposta per stessi dati); versioning via `ros_exports` table.

- **S5.3 — Migration 0016 + 0017 + 0018** (M)
  - **AC:** Tre migration applicate; FK validi.

- **S5.4 — Buyout cash ledger router** (M)
  - **AC:** POST inserisce evento; integra con `rtfc_balance` view (riduce obbligo da soddisfare); audit_log.

- **S5.5 — Reminder scheduler (cron-like + email)** (L)
  - **AC:** Job ricorrente (APScheduler in-process o cron container) che verifica `reminders.due_date <= NOW+30d AND status=pending` → invia email via SMTP cliente → marca `sent_at`; reminder seeded auto su `obligation_period` insert.
  - **Risk flags:** SMTP config + secrets management.

- **S5.6 — Verifier bundle PDF generator** (L)
  - **AC:** Estende `pdf_renderer` di E1 con template multi-page: cover + batch summary + GHG worksheets + event timeline + audit log excerpt + supply chain diagram; ZIP con hash manifest.

- **S5.7 — Frontend ROS export UI** (M)
  - **AC:** Pagina con anteprima dati + bottone "Export" + storico ros_exports.

- **S5.8 — Frontend reminders dashboard** (M)
  - **AC:** Lista reminders pending + ack action.

- **S5.9 — Frontend buyout entry** (M)
  - **AC:** Form inserimento evento buyout + storico tabellare.

**Risk flags:** schema ROS deve essere fetched prima; reminders dipendono da scheduler infra; verifier bundle scope creep.

---

### E6 — RTFO Phase 4: GHG Annex D automation

- **Goal:** Implementare metodologia Annex D controfattuale nel codice per il flusso RCF; integrazione DfT Carbon Calculator. Risponde a Fase 4 (gap §5).
- **Scope IN:** Implementazione formula Annex D RCF; import/export Carbon Calculator CSV; auto-compute `ghg_calculations` da daily inputs/production + emission factors; soglia 65% saving enforcement bloccante.
- **Scope OUT:** Annex D per altri feedstock (biogenic) — ELT-only.
- **Dependencies:** DfT pubblica Annex D formula stabilita (allegato all'essential guide); Carbon Calculator API o CSV format; emission factors database.
- **Migration(s) needed:**
  - `0019_emission_factors.py` — `emission_factors(id, factor_type enum {grid_electricity, diesel, natural_gas, transport_truck, transport_ship, ...}, region varchar, value_gCO2eq_unit, unit, source_doc_url, valid_from, valid_to, deleted_at)`.
  - `0020_annex_d_inputs.py` — `annex_d_inputs(ghg_calculation_id FK PK, counterfactual_landfill_gCO2eq, counterfactual_incineration_gCO2eq, transport_km, energy_kwh, ...)`.
- **Data model changes:** 2 nuove tabelle.
- **API endpoints needed:**
  - `POST /ghg/annex-d/compute?daily_production_id=` → auto-popola `ghg_calculations` + `annex_d_inputs`
  - `GET /ghg/emission-factors?type=&region=`
  - `POST /ghg/carbon-calculator/import` (multipart CSV upload)
  - `GET /ghg/carbon-calculator/export?period=`
- **Frontend changes:**
  - `/app/ghg/annex-d/` worksheet calculator
  - `/app/ghg/emission-factors/` admin

**Stories:**

- **S6.1 — Annex D formula spec doc** (M)
  - **AC:** `docs/annex-d-methodology.md` con formula completa RCF da DfT essential guide; cross-ref righe specifiche del doc fonte.

- **S6.2 — Migration 0019 emission_factors + seed** (M)
  - **AC:** Schema + seed da pubblicazione DfT 2025/2026.

- **S6.3 — Migration 0020 annex_d_inputs** (S)
  - **AC:** FK 1:1 con `ghg_calculations`.

- **S6.4 — Service `ghg_annex_d.py`** (L)
  - **AC:** Pure function `compute_annex_d(daily_production, emission_factors, annex_d_inputs) -> ghg_calculation_dict`; unit-tested con sample DfT.

- **S6.5 — Endpoint `POST /ghg/annex-d/compute`** (M)
  - **AC:** Calcola + persiste; idempotente per stesso input; ritorna 422 se sotto soglia 65% (advisory, non bloccante).

- **S6.6 — Carbon Calculator import/export** (L)
  - **AC:** Mapping CSV ↔ schema interno; verifica integrità (somma stadi = totale); idempotente.

- **S6.7 — Soglia 65% enforcement nel ledger** (M)
  - **AC:** `POST /rtfc-batches` con `ghg_calculation_id` cui `threshold_met=false` ritorna 409 con motivo; admin può override con flag + audit_log entry.

- **S6.8 — Frontend Annex D worksheet** (XL)
  - **AC:** Form multistep (transport km, energia kWh, fattori emissione, controfattuali) + preview compute live + save → ghg_calculation.

**Risk flags:** Annex D methodology può cambiare versione; emission factors regionali ELT-from-Colombia specifici.

---

## 3. Cross-cutting concerns

### Compliance & audit safety
- **MAI hard delete.** Tutte le entità nuove (feedstock, off_taker, verifier, rtfc_batch) hanno `deleted_at TIMESTAMP NULL` e filtrate `deleted_at IS NULL` nei query. RTFC events sono append-only — annullamento via event_type `cancelled`.
- **MAI scrivere `total_input_kg`** — colonna GENERATED. Estendere stessa disciplina a future colonne computed (litres se diventa generated).
- **AUTOCOMMIT obbligatorio per `REFRESH MATERIALIZED VIEW CONCURRENTLY`** — pattern in `routers/mass_balance.py` riusato per nuova `rtfc_balance` se MV.
- **Audit log immutable.** Ogni write su rtfc_batches/rtfc_events/buyout_events/ghg_calculations scrive entry audit_log; mai modificare audit_log; export CSV/JSON read-only.
- **Pydantic v2** — `model_dump()` non `.dict()`. Pattern già adottato.
- **Snapshot crittografico DB** in finestre regolatorie (E1 Day 5/6) — script `scripts/snapshot_db.sh` riusabile per Phase 3 ROS submission.
- **Soft-delete su supplier rectification** (E1 S1.7) come precedente metodologico per future ristrutturazioni.

### Testing strategy
- **E1 (5wd):** Smoke test E2E PDF generation su Gen 2025 (sample); test hash determinism (stesso input → stesso PDF? — disabilita timestamp embeded); test migration `0006` con verifica delta closure ≤ 0.01%.
- **E2 (Sprint 3):** Manual login E2E; `npm run build` zero errors; smoke deploy oistebio.usenexos.com.
- **E3-E6 (RTFO):** Pytest fixtures per ogni entity nuova (`tests/conftest.py`); test state machine rtfc_batches (E4); test carry-over 25% cap (E4); test soglia 65% (E6); test idempotenza ROS export (E5).
- **CI/CD:** Sprint 1 S1-14 (GitHub Actions) ancora aperto — prerequisito per E3+.

### Deploy considerations
- **Hetzner demo (oistebio.usenexos.com):** landing/ via PM2 + nginx; backend via Docker Compose `dft-back` su porta interna; Caddy 2 (non nginx) reverse proxy come da CLAUDE.md riga 16.
- **Production:** stesso stack; secrets via `.env` (mai committato); `JWT_SECRET` allineato backend↔landing/.env.local.
- **WeasyPrint deps** (E1 S1.2) richiedono Dockerfile patch — rebuild image, pull new image su Hetzner.
- **DB migrations** applicate via `alembic upgrade head` dentro container `dft-back`; backup pre-migration ad ogni release prod.
- **E5 reminder scheduler:** APScheduler in-process semplice; alternativa container cron dedicato se scaling necessario.

### Documentation deliverables
- **Aggiornare CLAUDE.md** dopo E1 con migration count corretto (8 dopo 0006-0008 E1+E3 partial) e routers aggiornati.
- **Aggiornare agentos-context.md** dopo E2 + E3 (sezioni §3, §4, §6 obsolete).
- **`docs/rtfo-feedstock-list.md`** (E3 S3.1).
- **`docs/ros-schema.md`** (E5 S5.1).
- **`docs/annex-d-methodology.md`** (E6 S6.1).
- **`docs/rtfo-gap-analysis.it.md`** aggiornato a v3 quando E3 chiude (rimuovere "MANCANTE" da §3.1-3.2-3.4).
- **BLUEPRINT.md v0.2** dopo E1 — riflettere split `daily_input`/`daily_production`, MV `mv_mass_balance_*` con litres, supplier_certificates m2m.

---

## 4. Risk register

| Risk | Impact | Mitigation | Owner |
|---|---|---|---|
| WeasyPrint system deps (cairo/pango) mancanti in container backend | Alto (blocca E1 Day 1) | Fallback `reportlab`; verifica `apt list --installed` Day 1 mattina | Team ingest |
| DfT rigetta nuovamente bundle Gen 2025 | Alto (pathway 2025 chiusa) | Track B prosegue; output riutilizzabile applicazioni 2026 | Crown Oil + OisteBio |
| Slittamento Day 6 (audit interno trova gap) | Alto (mancata submission Day 7) | Buffer mattina Day 7; preferire ritardo a submission incompleta | Team ingest |
| Migration `0006_supplier_rectification` introduce delta closure > 0.01% | Alto (rollback obbligato) | Dry-run su DB locale + query closure pre/post + scope limitato | Team ingest |
| Sprint 3 frontend partial state inconsistente con doc | Medio (gap S2.x non chiaramente identificati) | S2.11 DoD verification item-per-item | Frontend dev |
| Crown Oil non firma contratto formale → E4 bloccato | Alto (RTFC ledger non implementabile) | E3 procede indipendente; E4 deferred fino a Q4 risolto | Gianni + Crown Oil |
| LCF Delivery Unit non designa ELT come RCF eligible | Alto (RTFC assignment non possibile) | Documentare gap pubblicamente; richiesta designazione formale parallela al bundle Gen 2025 | OisteBio + Crown Oil |
| Schema ROS cambia tra E5 design e E5 release | Medio (rework su S5.1-S5.2) | Versionare `docs/ros-schema.md` con fetch date + monitorare DfT annunci | Team ingest |
| Annex D methodology update DfT | Medio (rework E6) | Pure function isolated in `services/ghg_annex_d.py`; versioning su `ghg_methodology.methodology_version` | Team ingest |
| JWT_SECRET disallineato dev/prod (Sprint 3) | Medio (login rotto in prod) | Documentare in `.env.example`; validate in middleware startup | Frontend dev |
| Database snapshot Day 5/6 non riusciti per spazio disco | Medio (no evidence integrity) | Pre-flight `df -h`; pulire snapshot vecchi | Team ingest |
| WSL / Linux file mode bits su PDF immutability | Basso (hash valido) | Hash su contenuto bytes, non file metadata | Team ingest |
| Carry-over 25% mal calcolato | Alto (E4 — RTFC assegnati eccedenti) | Test specifici S4.11; cap server-side; audit_log su ogni carry-over | Team ingest |
| Reminders email mai inviate (SMTP misconfig) | Medio (E5 — scadenza 15-set persa) | Health check job + fallback SMS/Slack | Team ingest |

---

## 5. Open decisions for client

| # | Decisione | Blocca | Owner | Target |
|---|---|---|---|---|
| D1 | Conferma scritta DfT decorrenza 5wd, scope (Gen 2025 only), deadline esatta (21 mag 23:59 UK) | E1 (assunzione di lavoro corrente) | Crown Oil → DfT contact | Day 1 EOD |
| D2 | Persistenza `litres_eu`/`litres_plus` come colonne fisiche su `daily_production`? | E1 S1.1 (migration 0007 condizionale) | Team ingest + Crown Oil + DfT preference | Day 1 |
| D3 | Mapping definitivo fornitori → collecting points per riclassificazione Gen 2025 | E1 S1.7 (migration 0006) | OisteBio | Day 1-2 |
| D4 | Crown Oil contratta su base fisica (segregata) o mass-balance? (gap §7 Q4) | E4 S4.1 (off_takers.contract_basis seed) | Crown Oil | Post Crown Oil meeting |
| D5 | ELT designato dalla LCF Delivery Unit come feedstock RCF-eligible? (gap §7 Q3) | E4 (RTFC assignment non possibile senza designazione) | OisteBio + Crown Oil → DfT LCF Unit | Parallelo al bundle Gen 2025 |
| D6 | Verifier RTFO-recognised per bundle DEV-P100? (gap §7 Q5) | E4 S4.2 + E5 S5.6 (verifier bundle scope) | Crown Oil → ricerca verifier | Pre E4 start |
| D7 | Fetch schema ROS ufficiale (DfT API o doc scaricabile) | E5 S5.1 | Team ingest | Pre E5 start |
| D8 | Configurazione SMTP per reminder emails (E5 S5.5) | E5 reminders | Cliente + DevOps | Pre E5 start |
| D9 | Annex D methodology version target (essential guide rev attuale) | E6 S6.1 | Team ingest + Crown Oil | Pre E6 start |
| D10 | Carbon Calculator availability (API vs CSV-only) | E6 S6.6 | DfT contact | Pre E6 start |

---

## 6. Naming + Plane mapping convention

- **Workspace:** `xbitagency` | **Project:** `DFTEN` (DFT Energy) | **Project ID:** `b515ded8-3a55-4764-be0c-a010941e847f`.
- **Epic** → Plane **Module** (name = `e{N}-<slug>`, descrizione = goal + scope).
- **Story** → Plane **Issue** con label `story` + Module link; titolo formato `S{N}.{M} — <title>`.
- **Task** dentro story → preferenza **checklist nel description** (T1, T2, T3, T4…) con voce per file/endpoint tocco; alternativa Plane **sub-issue** se task ha dimensione > 0.5 giorno.
- **Acceptance criteria** → sezione fissa "AC" nel description (bulleted).
- **Complexity label:** `xs` / `s` / `m` / `l` / `xl` (mapping: xs=<2h, s=2-8h, m=1-2d, l=3-5d, xl=>1w → da splittare).
- **Risk flags** → label `risk-high` / `risk-medium` se applicabili.
- **Dependencies** → Plane Issue Relations (blocked_by / blocks).
- **Cross-ref source docs** nel description con link relativi (es. `docs/rtfo-gap-analysis.it.md §3.2`).
- **Migration deliverable** nel description con path target (es. `backend/alembic/versions/0008_feedstocks.py`).
- **Naming epic** lowercase-with-dashes; **naming story** spazi e maiuscole IT human-readable.

**Issue count target raggiunto:**
- E1: 18 storie
- E2: 11 storie
- E3: 9 storie
- E4: 13 storie
- E5: 9 storie
- E6: 8 storie
- **Totale: 68 storie** (sopra il target 40-60; E4/E5/E6 sono Plane-staged ma non in flight finché D4/D5/D6/D7 risolti).
