# DFT Project — Blueprint Full-Stack Mass Balance

**Status:** Draft v0.1 — pre-implementation
**Created:** 2026-05-07
**Owner:** XbitAgency / Gianni
**Source data:** `Girardot producciòn Enero 2025.xlsx` (Drive folder `1jC39kiulY-6utuYsuhY2SgNqRpkQtiB5`)
**Isolation:** standalone — zero coupling con BiNova/AgentOS/NexOS

---

## 1. Scope

Sistema di tracciabilità mass balance per impianto biofuel/recycling Girardot (Colombia). Sostituisce foglio Excel con database normalizzato + frontend per visualizzazione, data entry operatore, generazione PDF certificatore (ISCC / EU RED II).

**Obiettivi:**
- Eliminare `#REF!` errors e celle rotte del file xlsx attuale.
- Audit trail completo (chi/quando/cosa modifica).
- Closure mass balance verificabile automaticamente.
- Export PDF mensile/trimestrale per certificatore.
- Data entry guidato (no errori operatore).

---

## 2. Stack tecnologico

| Layer | Tech | Motivo |
|-------|------|--------|
| Frontend | Next.js 14 (App Router) + Tailwind + shadcn/ui | SSR, ottimo DX, componenti accessibili |
| Charts | Recharts | Leggero, integra con React |
| Tables | TanStack Table + TanStack Query | Filtri/sort/paginazione lato client |
| Forms | react-hook-form + zod | Validazione type-safe |
| Backend | FastAPI (Python 3.12) + SQLAlchemy 2.0 + Pydantic v2 | Async, schema validation, auto OpenAPI |
| DB | PostgreSQL 16 | Robust, ottimo per analytics, JSON support |
| PDF gen | WeasyPrint (HTML→PDF) | Template HTML/CSS riusabile, no licenze |
| Auth | NextAuth (credentials + magic link) | Self-hosted, ruoli custom |
| Migrations | Alembic | Standard Python ecosystem |
| Container | Docker Compose | Deploy isolato, riproducibile |
| Hosting | Hetzner (container dedicato) | Già usato per altri progetti |

---

## 3. Database schema

### Anagrafiche

```sql
CREATE TABLE suppliers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  code VARCHAR(20) UNIQUE,
  country VARCHAR(2) DEFAULT 'CO',
  active BOOLEAN DEFAULT TRUE,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE contracts (
  id SERIAL PRIMARY KEY,
  code VARCHAR(20) NOT NULL UNIQUE,
  supplier_id INT NOT NULL REFERENCES suppliers(id),
  start_date DATE NOT NULL,
  end_date DATE,
  total_kg_committed NUMERIC(12,2),
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE certificates (
  id SERIAL PRIMARY KEY,
  cert_number VARCHAR(50) NOT NULL UNIQUE,
  supplier_id INT NOT NULL REFERENCES suppliers(id),
  issued_at DATE NOT NULL,
  expires_at DATE,
  scheme VARCHAR(20) DEFAULT 'ISCC',
  document_url TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Core: daily entries

```sql
CREATE TABLE daily_entries (
  id BIGSERIAL PRIMARY KEY,
  entry_date DATE NOT NULL,
  entry_time TIME,

  -- references
  supplier_id INT REFERENCES suppliers(id),
  contract_id INT REFERENCES contracts(id),
  certificate_id INT REFERENCES certificates(id),
  ersv_number VARCHAR(50),

  -- input weights
  car_kg NUMERIC(10,2) DEFAULT 0,
  truck_kg NUMERIC(10,2) DEFAULT 0,
  special_kg NUMERIC(10,2) DEFAULT 0,
  total_input_kg NUMERIC(10,2) GENERATED ALWAYS AS (
    COALESCE(car_kg,0) + COALESCE(truck_kg,0) + COALESCE(special_kg,0)
  ) STORED,

  -- veg %
  theor_veg_pct NUMERIC(5,2),
  manuf_veg_pct NUMERIC(5,2),

  -- production
  -- NB: eu_prod_kg = kg di prodotto finale DEV-P100 (refined pyrolysis oil OisteBio, output certificato EU verso Crown Oil UK)
  kg_to_production NUMERIC(10,2),
  eu_prod_kg NUMERIC(10,2),       -- DEV-P100 (refined pyrolysis oil) — bucket export certificato
  plus_prod_kg NUMERIC(10,2),

  -- analysis
  c14_analysis BOOLEAN DEFAULT FALSE,
  c14_value NUMERIC(5,2),

  -- byproducts
  carbon_black_kg NUMERIC(10,2),
  metal_scrap_kg NUMERIC(10,2),

  -- losses
  h2o_pct NUMERIC(5,2),
  gas_syngas_pct NUMERIC(5,2),
  losses_kg NUMERIC(10,2),

  -- output
  output_eu_kg NUMERIC(10,2),
  contract_ref VARCHAR(20),
  pos_number VARCHAR(20),

  -- audit
  source_file VARCHAR(255),
  source_row INT,
  created_by INT REFERENCES users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_by INT REFERENCES users(id),
  updated_at TIMESTAMP DEFAULT NOW(),
  deleted_at TIMESTAMP
);

CREATE INDEX idx_daily_entries_date ON daily_entries(entry_date);
CREATE INDEX idx_daily_entries_supplier ON daily_entries(supplier_id);
CREATE INDEX idx_daily_entries_contract ON daily_entries(contract_id);
```

### Aggregati pre-calcolati (materialized views)

```sql
CREATE MATERIALIZED VIEW mv_mass_balance_daily AS
SELECT
  entry_date,
  COUNT(*) AS entries_count,
  SUM(total_input_kg) AS input_kg,
  SUM(eu_prod_kg) AS eu_prod_kg,
  SUM(plus_prod_kg) AS plus_prod_kg,
  SUM(output_eu_kg) AS output_eu_kg,
  SUM(carbon_black_kg) AS carbon_black_kg,
  SUM(metal_scrap_kg) AS metal_scrap_kg,
  SUM(losses_kg) AS losses_kg,
  AVG(theor_veg_pct) AS avg_theor_veg_pct,
  AVG(manuf_veg_pct) AS avg_manuf_veg_pct,
  (SUM(eu_prod_kg) + SUM(plus_prod_kg) + SUM(carbon_black_kg) + SUM(metal_scrap_kg) + SUM(losses_kg)) AS total_output_kg,
  (SUM(total_input_kg) - (SUM(eu_prod_kg) + SUM(plus_prod_kg) + SUM(carbon_black_kg) + SUM(metal_scrap_kg) + SUM(losses_kg))) AS closure_diff_kg
FROM daily_entries
WHERE deleted_at IS NULL
GROUP BY entry_date;

CREATE MATERIALIZED VIEW mv_mass_balance_monthly AS
SELECT
  date_trunc('month', entry_date) AS month,
  supplier_id,
  SUM(total_input_kg) AS input_kg,
  SUM(eu_prod_kg) AS eu_prod_kg,
  SUM(plus_prod_kg) AS plus_prod_kg,
  SUM(output_eu_kg) AS output_eu_kg
FROM daily_entries
WHERE deleted_at IS NULL
GROUP BY date_trunc('month', entry_date), supplier_id;
```

### Auth + audit

```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255),
  full_name VARCHAR(100),
  role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'operator', 'viewer', 'certifier')),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP
);

CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  action VARCHAR(20) NOT NULL,  -- INSERT, UPDATE, DELETE
  table_name VARCHAR(50) NOT NULL,
  record_id BIGINT NOT NULL,
  old_values JSONB,
  new_values JSONB,
  ip_address INET,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. Backend API (FastAPI)

### Endpoint principali

```
POST   /auth/login
POST   /auth/logout
GET    /auth/me

GET    /suppliers
POST   /suppliers
GET    /suppliers/{id}
PATCH  /suppliers/{id}

GET    /contracts
POST   /contracts
GET    /contracts/{id}

GET    /certificates
POST   /certificates

GET    /daily-entries           # filtri: date_from, date_to, supplier_id, contract_id
POST   /daily-entries
GET    /daily-entries/{id}
PATCH  /daily-entries/{id}
DELETE /daily-entries/{id}      # soft delete

GET    /reports/mass-balance/daily?from=&to=
GET    /reports/mass-balance/monthly?year=
GET    /reports/closure?period=
GET    /reports/by-supplier?from=&to=

POST   /pdf/mass-balance        # body: period, format → returns PDF stream
POST   /pdf/certificate         # body: month, supplier_id

POST   /import/xlsx             # admin only — bulk import file storico
GET    /audit-log               # admin only
```

### Validazione business rules

- `total_input_kg = car_kg + truck_kg + special_kg` (auto-calc)
- `0 ≤ theor_veg_pct ≤ 100`
- `0 ≤ manuf_veg_pct ≤ 100`
- Closure check: warning se `|input - (eu_prod + plus_prod + byproducts + losses)| > 1%`
- Date entry non futura
- Supplier/contract devono essere active

---

## 5. Frontend (Next.js)

### Routes

```
/                           # Dashboard (KPI + grafici)
/login
/entries                    # tabella con filtri
/entries/new                # form nuova entry
/entries/[id]               # detail + edit
/suppliers                  # admin
/contracts                  # admin
/certificates               # admin
/reports
/reports/mass-balance       # vista chiusura mass balance
/reports/by-supplier        # breakdown fornitore
/reports/monthly            # vista mensile
/pdf                        # genera PDF (period picker)
/admin
/admin/users
/admin/audit-log
/admin/import               # upload xlsx storico
```

### Componenti chiave

- `<DailyEntryForm>` — 20 campi schema, validazione zod, auto-calc derived
- `<DailyEntryTable>` — TanStack Table, filtri, sort, paginazione, export CSV
- `<MassBalanceChart>` — Recharts, time series input vs output
- `<ClosureGauge>` — semaforo visuale closure %
- `<SupplierBreakdown>` — pie chart input per fornitore
- `<PdfPreview>` — preview HTML pre-export

### UX guidelines

- Form data entry: keyboard-first, Tab navigation, Enter conferma riga
- Validazione inline (red border + tooltip messaggio)
- Auto-save draft (localStorage) — recovery se crash browser
- Mobile responsive (operatore impianto può usare tablet)
- Dark mode opzionale

---

## 6. PDF generation

### Template ISCC / EU RED II

- Header: logo + impianto + periodo + cert scheme
- Sezione 1: Mass Balance Summary (input/output/closure)
- Sezione 2: Breakdown fornitore (tabella)
- Sezione 3: Daily entries (tabella riassuntiva)
- Sezione 4: Veg matrix sampling (theor vs manuf)
- Sezione 5: Byproducts + losses
- Footer: firma operatore, firma certificatore, timestamp generazione

**Tech:** WeasyPrint legge HTML+CSS (template Jinja2) → PDF/A.

---

## 7. Roadmap incrementale

### Sprint 1 — Foundation (1 settimana)
- Repo setup (`dft-project`)
- Docker Compose: Postgres + FastAPI + Next.js
- DB schema + migrations Alembic
- Seed data fornitori/contratti dal file Girardot
- Backend: auth + CRUD daily_entries (no UI ancora)
- Test API con curl/Postman

### Sprint 2 — Ingest storico + read API (3-4 giorni)
- Parser xlsx Girardot (pandas + openpyxl)
- Script ingest one-shot con dry-run + report errori
- Materialized views + refresh strategy
- Endpoint reports (mass balance, by supplier, monthly)

### Sprint 3 — Frontend dashboard integrato (1 settimana)
**Approccio**: estendere `landing/` (Next.js 14 esistente, deploy oistebio.usenexos.com) con area protetta `/app/*`. NO progetto frontend separato — single app, single deploy.
- shadcn/ui + UI primitives in `landing/`
- API client tipizzato (openapi-typescript da backend)
- Auth flow: `/login` form → httpOnly cookie → middleware protegge `/app/*`
- Layout dashboard (sidebar + topbar)
- Dashboard home KPI + sparkline
- 3 report views: mass-balance daily/monthly, by-supplier, closure-status
- Anagrafiche read-only views (CRUD in Sprint 4)

Vedi `docs/sprint-3-frontend.md` per breakdown completo issues.

### Sprint 4 — Data entry + admin (1 settimana)
- Form nuova entry (tutti i campi)
- Form edit entry
- Bulk paste modal
- Pagine admin: suppliers, contracts, certificates, users
- Audit log viewer

### Sprint 5 — PDF + deploy (3-4 giorni)
- WeasyPrint setup + template HTML/CSS
- Endpoint PDF gen (mass balance + certificato)
- Preview frontend prima export
- Deploy Docker Hetzner
- Backup automatico DB (cron)
- HTTPS + dominio

### Sprint 6 — Polish + handover (3-4 giorni)
- QA E2E con Playwright
- Documentazione utente (PDF + video screencast)
- Training operatore (sessione live cliente)
- Setup utenti finali

**Tempistica totale:** ~5-6 settimane lavorative (single dev) — dimezzabile con team.

---

## 8. Decisioni aperte (post-call cliente)

| # | Domanda | Default | Risposta |
|---|---------|---------|----------|
| 1 | Nome cliente confermato | `dft-project` | TBD |
| 2 | Multi-impianto futuro o solo Girardot | Solo Girardot | TBD |
| 3 | PDF template fornito da cliente | Template ISCC standard | TBD |
| 4 | Hosting | Hetzner XbitAgency | TBD |
| 5 | Auth: SSO cliente o gestita da noi | NextAuth credentials | TBD |
| 6 | Lingua UI | IT + EN | TBD |
| 7 | Storico 2024 da importare | No (solo 2025+) | TBD |
| 8 | Backup retention | 30 giorni daily + 12 mesi monthly | TBD |
| 9 | Mobile UI obbligatoria | Sì (tablet operatore) | TBD |
| 10 | Integrazione ERP cliente | No (export CSV/PDF solo) | TBD |

---

## 9. Risk register

| Risk | Mitigazione |
|------|-------------|
| Schema xlsx variabile mese-mese | Parser robusto + validazione + report errori manuali |
| Operatore inserisce dati errati | Validazione inline + audit log + workflow approvazione |
| PDF non conforme a richiesta certificatore | Mock template + review cliente PRIMA implementazione |
| Performance con 10K+ righe | Indici DB + materialized views + paginazione |
| Backup persi | Backup offsite Hetzner + dump quotidiano S3-compatible |
| Compliance GDPR / data residency | Hosting EU (Hetzner Falkenstein/Helsinki) — già OK |

---

## 10. Sicurezza

- Password hash: bcrypt (cost 12)
- TLS obbligatorio (Let's Encrypt)
- Rate limiting su auth endpoints
- Audit log immutabile (append-only)
- Soft delete (no hard delete da UI — solo admin via DB)
- Backup criptati at-rest
- Secrets via env vars (no commit `.env`)
- CSP header strict su frontend
- SQL injection prevenuta da SQLAlchemy ORM

---

## 11. Struttura repo

```
dft-project/
├── BLUEPRINT.md            # questo file
├── README.md               # quickstart dev
├── docker-compose.yml
├── .env.sample
├── docs/
│   ├── api.md
│   ├── deploy.md
│   ├── pdf-template.md
│   └── data-dictionary.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── pdf/
│   │   └── core/
│   ├── alembic/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── tests/
├── db/
│   ├── seed.sql
│   └── init.sql
└── scripts/
    ├── ingest_xlsx.py
    └── backup.sh
```

---

## 12. Next actions immediate

1. ✅ Blueprint creato (`/mnt/c/Users/User/dft-project/BLUEPRINT.md`)
2. ⏳ Cliente conferma decisioni aperte (sezione 8)
3. ⏳ `git init` + push repo (GitHub privato)
4. ⏳ Sprint 1 kickoff: scaffold Docker + DB + auth

---

**Riferimenti:**
- File source: Drive `1FWeZs6nxmM_STzFZLGFVpPCBU877Uukw`
- Folder: `1jC39kiulY-6utuYsuhY2SgNqRpkQtiB5` (2025)
- Cliente: TBD
- Repo: TBD
