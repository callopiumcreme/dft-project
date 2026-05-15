# DFT — Riepilogo lavoro per cliente

**Periodo:** 2026-05-07 → 2026-05-13 (1 settimana intensiva)
**Commit totali:** 88 (46 feat, 14 fix, 16 docs, 12 chore/refactor/test)
**Destinatario:** OisteBio / Crown Oil / DfT

---

## 1. Cosa è stato consegnato

### A) Piattaforma DFT — applicazione web completa

Sostituisce il foglio Excel Girardot con sistema database + dashboard online.

**Backend (FastAPI + PostgreSQL):**
- Schema DB completo: suppliers, contracts, certificates, daily_inputs, daily_production, audit_log, users
- Autenticazione JWT con ruoli (admin, operator, viewer, certifier)
- Audit trail completo (chi/quando/cosa modifica) — requisito ISCC/RTFO
- Soft delete + restore su tutte le entità (zero perdita storico)
- Materialized views per report mass balance (daily + monthly)
- 5 migrations Alembic versionate

**Frontend (Next.js dashboard `/app/*`):**
- Login + protezione route con cookie httpOnly
- Dashboard KPI con grafico input vs output
- CRUD completo: daily inputs, daily production, suppliers, contracts, certificates, users
- 3 report ufficiali:
  - **Mass balance** daily + monthly, con filtro fornitore, conversione kg→litri, KPI split EU/Plus/Totale, colonna C14, accordion dettaglio giornaliero
  - **By-supplier** pie chart + ranking + export CSV
  - **Closure status** semaforo con bucket di tolleranza + filtro + CSV
- Audit log viewer (admin)
- UI multilingua IT → EN
- Screenshot in `screenshots-jan2025/` (11 viste)

### B) Ingest automatico file Excel Girardot

Parser xlsx production-ready che ha già caricato i dati reali di Gennaio 2025.

**Fix critici risolti durante validazione dati:**
- Recupero righe self-declared ≤5 TON (mai parsate prima)
- Riconoscimento aggregati K+L+M+O vs righe dettaglio
- Skip aggregate mensile TOTAL a fine foglio
- Skip aggregate date-row appartenente al giorno precedente
- Fix _as_time per orari stringa AM/PM (20 righe dettaglio recuperate)
- Canonicalizzazione token null + recupero righe perse

### C) Compliance RTFO / DfT — documentazione completa

- **`rtfo-essential-guide.md`** — guida sintetica scheme RTFO UK
- **`rtfo-gap-analysis.md` + `.it.md`** — gap analysis bilingue: cosa serve per ottenere RTFC su produzione Girardot
- **`dft-action-plan-2026-05.md`** v3 — piano operativo focalizzato sul bundle Gennaio 2025
- **2 email draft 2026-05-13:**
  - OisteBio → Crown Oil (briefing intent)
  - Crown Oil → DfT (richiesta formale estensione scope)

### D) Landing oistebio.usenexos.com

- Import sito marketing + dashboard integrata stesso codebase Next.js
- Brief landing + brief web developer
- Tooling deploy Hetzner (PM2 + Caddy)
- Hardening sicurezza: header injection, rate limit, sanitization contact form (13/13 test pass)

---

## 2. Dati caricati

- File: `Girardot producciòn Enero 2025.xlsx`
- Periodo coperto: Gennaio 2025 (scope esteso fino Agosto 2025 in pipeline)
- Tutte le righe ricostruite e validate (zero `#REF!`, zero perdita righe)

---

## 3. Stato attuale

| Area | Stato |
|------|-------|
| Backend API | ✅ Production-ready |
| Frontend dashboard | ✅ Tutte le viste live |
| Parser xlsx | ✅ Validato su dati reali Gen 2025 |
| Autenticazione + ruoli | ✅ JWT + audit |
| Report mass balance | ✅ Daily + monthly + by-supplier + closure |
| Sicurezza | ✅ Hardening pass eseguito |
| Compliance RTFO docs | ✅ Gap analysis + action plan |
| Deploy demo | ⏳ Hetzner pronto (`91.98.82.20`), domini da puntare |
| Scope esteso Feb→Ago 2025 | ⏳ In pipeline post-meeting Crown Oil |

---

## 4. Prossimi passi

1. Meeting Crown Oil (2026-05-13) — presentazione piattaforma + richiesta estensione DfT
2. Caricamento file production Feb→Ago 2025
3. Deploy demo client su sottodominio dedicato
4. Generazione PDF certificatore (Sprint 4 residuo)

---

## 5. Vantaggi consegnati vs Excel attuale

- Zero errori `#REF!` o celle rotte
- Audit trail per certificatore ISCC/RTFO
- Closure mass balance verificabile automaticamente
- Multi-utente con ruoli
- Export CSV per report ufficiali
- Restore record cancellati
- Backup database vs file Excel singolo
