# DFT Project — Analisi approfondita pre-parametrizzazione AgentOS

**Data analisi:** 2026-05-08
**Versione:** 1.0
**Scope:** SCENARIO-B — documentazione tecnica completa per configurazione agenti AgentOS

---

## 1. Dominio di business

**Progetto:** Sistema di tracciabilità mass balance per impianto biofuel/recycling Girardot (Colombia).

**Cliente:** TBD (XbitAgency gestisce il progetto, cliente finale da confermare).

**Problema risolto:** Sostituisce foglio Excel con `#REF!` errors. Genera audit trail + PDF certificatore ISCC/EU RED II.

### Concetti chiave del dominio

| Termine | Significato |
|---------|-------------|
| **Mass balance** | Verifica input ≈ output: `input_kg = eu_prod + plus_prod + byproducts + losses`. Chiusura entro ±1% |
| **Daily entry** | Riga di tracciabilità giornaliera: pesi vehicoli, produzione, sottoprodotti, perdite |
| **ISCC / EU RED II** | Schemi di certificazione per biofuel sostenibile. Richiedono PDF mensile firmato |
| **Supplier** | Fornitore di materia prima (rifiuti organici, oli esausti, ecc.) |
| **Contract** | Accordo fornitore-impianto con kg impegnati e date validità |
| **Certificate** | Certificato ISCC del fornitore (scadente — va monitorato) |
| **c14 analysis** | Analisi al carbonio-14 per verificare l'origine biogenica del materiale |
| **ERSV number** | Numero di tracciatura del vettore di trasporto |
| **Closure diff** | `total_input_kg − (eu_prod + plus_prod + carbon_black + metal_scrap + losses)` — deve essere ≈ 0 |

---

## 2. Stack tecnologico

| Layer | Tech | Versione | Note |
|-------|------|----------|------|
| Backend | FastAPI | 0.x | Async, SQLAlchemy 2.0 |
| ORM | SQLAlchemy | 2.0 | `async_sessionmaker`, `AsyncSession` |
| Schemas | Pydantic | v2 | `model_dump()` non `.dict()` |
| Migrations | Alembic | latest | 8 migration files in `versions/` |
| DB | PostgreSQL | 16 | Materialized views, GENERATED columns |
| Auth | JWT (python-jose) | — | Bearer token, 8h TTL, stateless |
| Password | bcrypt (passlib) | cost 12 | |
| Frontend | Next.js | 14 (App Router) | Stub — Dockerfile solo, no app code ancora |
| Landing | Next.js | 14 | In `/landing/`, già built |
| Reverse proxy | Caddy | 2-alpine | Non nginx — auto HTTPS |
| Containers | Docker Compose | — | 4 servizi: db, backend, frontend, caddy |
| Python lint | ruff + mypy + pre-commit | — | Già configurati (S1-13 DONE) |

---

## 3. Struttura repository

```
dft-project/
├── BLUEPRINT.md                  # Specifica tecnica completa (fonte di verità)
├── README.md                     # Quickstart dev
├── docker-compose.yml            # 4 servizi: db + backend + frontend + caddy
├── Caddyfile                     # Config reverse proxy (HTTPS auto)
├── .env.sample                   # Template variabili d'ambiente
├── .pre-commit-config.yaml       # ruff + mypy hooks
│
├── backend/
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 0001_init_anagrafiche.py        # suppliers, contracts, certificates
│   │       ├── 0002_add_search_indexes.py      # indici performance (ridondanti rimossi in 0002)
│   │       ├── 0003_daily_entries.py           # tabella daily_entries + GENERATED column
│   │       ├── 0004_users_audit_log.py         # users + audit_log
│   │       ├── 0005_daily_entries_hours_description.py  # campi hours + description aggiunti
│   │       ├── 0006_certificates_status_updated_at.py   # status + updated_at su certificates
│   │       ├── 0007_seed_suppliers_certificates.py      # seed dati Girardot
│   │       └── 0008_materialized_views.py      # mv_mass_balance_daily + mv_mass_balance_monthly
│   └── app/
│       ├── main.py               # FastAPI app, include_router per tutti i router
│       ├── core/
│       │   └── security.py       # JWT encode/decode, bcrypt hash/verify
│       ├── db/
│       │   ├── base.py           # DeclarativeBase
│       │   └── session.py        # engine, async_session_factory, get_db()
│       ├── models/
│       │   ├── __init__.py       # importa tutti i modelli
│       │   ├── supplier.py
│       │   ├── contract.py
│       │   ├── certificate.py
│       │   ├── daily_entry.py    # modello principale — 30 campi
│       │   ├── user.py
│       │   └── audit_log.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── supplier.py
│       │   ├── contract.py
│       │   ├── certificate.py
│       │   ├── daily_entry.py    # DailyEntryCreate, DailyEntryRead, DailyEntryUpdate
│       │   ├── user.py
│       │   └── audit_log.py
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── auth.py           # POST /auth/login, POST /auth/logout, GET /auth/me
│       │   ├── suppliers.py      # CRUD /suppliers
│       │   ├── contracts.py      # CRUD /contracts
│       │   ├── certificates.py   # CRUD /certificates
│       │   ├── daily_entries.py  # CRUD /daily-entries (soft delete + audit log)
│       │   └── mass_balance.py   # GET /mass-balance/daily|monthly, POST /mass-balance/refresh
│       └── tests/
│           ├── test_refresh_concurrently.py
│           └── test_s1_11_daily_entries_auth.py
│
├── frontend/
│   └── Dockerfile                # Stub — app Next.js non ancora implementata
│
├── landing/                      # Sito landing separato (già built con Next.js 14)
│   ├── content/blog/
│   ├── package.json
│   └── .next/                    # Build già presente
│
├── db/
│   ├── init.sql                  # Init PostgreSQL (ruoli, extensions)
│   └── seed.sql
│
└── docs/
    ├── brief-landing-page.md
    ├── brief-web-developer.md
    └── agentos-context.md        # questo file
```

---

## 4. Database schema — stato reale

### Tabelle

| Tabella | Campi chiave | Note |
|---------|-------------|------|
| `suppliers` | id, name, code, country, active, notes | Anagrafica fornitori |
| `contracts` | id, code, supplier_id, start_date, end_date, total_kg_committed | Contratti fornitore |
| `certificates` | id, cert_number, supplier_id, issued_at, expires_at, scheme, status | Certificati ISCC |
| `daily_entries` | 30 campi (vedi §4.1) | Tabella principale — audit + soft delete |
| `users` | id, email, password_hash, full_name, role, active | Ruoli: admin/operator/viewer/certifier |
| `audit_log` | user_id, action, table_name, record_id, old_values, new_values | Append-only, JSONB |

### Tabella daily_entries — campi completi

| Campo | Tipo | Note |
|-------|------|------|
| `id` | BIGSERIAL | PK |
| `entry_date` | DATE | obbligatorio |
| `entry_time` | TIME | opzionale |
| `supplier_id` | FK → suppliers | |
| `contract_id` | FK → contracts | |
| `certificate_id` | FK → certificates | |
| `ersv_number` | VARCHAR(50) | numero vettore |
| `car_kg` | NUMERIC(10,2) | input auto |
| `truck_kg` | NUMERIC(10,2) | input camion |
| `special_kg` | NUMERIC(10,2) | input speciale |
| `total_input_kg` | GENERATED | `car_kg + truck_kg + special_kg` — **read-only in ORM** |
| `theor_veg_pct` | NUMERIC(5,2) | % veg teorica |
| `manuf_veg_pct` | NUMERIC(5,2) | % veg manifattura |
| `kg_to_production` | NUMERIC(10,2) | |
| `eu_prod_kg` | NUMERIC(10,2) | produzione EU |
| `plus_prod_kg` | NUMERIC(10,2) | produzione plus |
| `c14_analysis` | BOOLEAN | |
| `c14_value` | NUMERIC(5,2) | |
| `carbon_black_kg` | NUMERIC(10,2) | sottoprodotto |
| `metal_scrap_kg` | NUMERIC(10,2) | sottoprodotto |
| `h2o_pct` | NUMERIC(5,2) | perdita acqua % |
| `gas_syngas_pct` | NUMERIC(5,2) | perdita gas % |
| `losses_kg` | NUMERIC(10,2) | perdite totali kg |
| `output_eu_kg` | NUMERIC(10,2) | output EU |
| `contract_ref` | VARCHAR(20) | |
| `pos_number` | VARCHAR(20) | |
| `hours` | NUMERIC(5,2) | ore operazione (aggiunto in 0005) |
| `description` | TEXT | note libere (aggiunto in 0005) |
| `source_file` | VARCHAR(255) | per import xlsx |
| `source_row` | INT | per tracciare riga xlsx originale |
| `created_by` | INT → users.id | |
| `created_at` | TIMESTAMP | |
| `updated_by` | INT → users.id | |
| `updated_at` | TIMESTAMP | |
| `deleted_at` | TIMESTAMP | NULL = non cancellato (soft delete) |

### Materialized Views

| View | Aggregazione | Aggiornamento |
|------|-------------|---------------|
| `mv_mass_balance_daily` | Per `entry_date`: input_kg, eu_prod, plus_prod, output_eu, byproducts, losses, closure_diff | `POST /mass-balance/refresh` → `refresh_mass_balance_views()` in AUTOCOMMIT |
| `mv_mass_balance_monthly` | Per `month` + `supplier_id`: aggregati mensili | Stessa funzione |

**CRITICO:** `REFRESH MATERIALIZED VIEW CONCURRENTLY` non può girare dentro una transazione. L'endpoint usa `engine.execution_options(isolation_level="AUTOCOMMIT")`.

---

## 5. API contract

### Auth
```
POST /auth/login      body: {email, password}  → {access_token, token_type}
POST /auth/logout     204 (stateless — client scarta token)
GET  /auth/me         → UserRead (richiede Bearer)
```

### CRUD standard (tutti richiedono Bearer salvo GET)
```
GET|POST  /suppliers
GET|PATCH /suppliers/{id}

GET|POST  /contracts
GET       /contracts/{id}

GET|POST  /certificates
GET       /certificates/{id}

GET|POST  /daily-entries        filtri: date_from, date_to, supplier_id, contract_id, skip, limit
GET       /daily-entries/{id}
PATCH     /daily-entries/{id}   + audit log automatico
DELETE    /daily-entries/{id}   soft delete (sets deleted_at) + audit log
```

### Mass balance
```
GET  /mass-balance/daily    filtri: date_from, date_to
GET  /mass-balance/monthly  filtri: month_from, month_to, supplier_id
POST /mass-balance/refresh  aggiorna le materialized views
```

### Health
```
GET /health → {"status": "ok", "version": "0.1.0"}
```

---

## 6. Autenticazione

- **Tipo:** JWT Bearer (stateless)
- **TTL:** 480 minuti (8 ore) — configurabile via `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Payload JWT:** `{sub: email, role: role, exp: timestamp}`
- **Ruoli:** `admin`, `operator`, `viewer`, `certifier`
- **Dipendenza FastAPI:** `CurrentUser = Annotated[User, Depends(_get_current_user)]`
- **Audit:** ogni write su `daily_entries` scrive riga in `audit_log` con IP client

---

## 7. Variabili d'ambiente

| Var | Default | Obbligatoria | Note |
|-----|---------|-------------|------|
| `POSTGRES_DB` | `dft` | sì | |
| `POSTGRES_USER` | `dft` | sì | |
| `POSTGRES_PASSWORD` | — | sì | changeme in .env.sample |
| `SECRET_KEY` | — | sì | `openssl rand -hex 32` |
| `DATABASE_URL` | `postgresql+asyncpg://dft:dft@db:5432/dft` | no | override per test |
| `JWT_SECRET` | `changeme-dft-secret-key-2026` | sì in prod | uguale a SECRET_KEY |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | no | |
| `ENVIRONMENT` | `development` | no | |
| `NEXTAUTH_URL` | `http://localhost:3000` | sì | |
| `NEXTAUTH_SECRET` | — | sì | `openssl rand -hex 32` |
| `NEXT_PUBLIC_API_URL` | `/api` | no | URL backend dal browser |

---

## 8. Business rules obbligatorie

1. `total_input_kg` è GENERATED ALWAYS — mai scrivere questo campo via ORM/API
2. Closure check: `|input_kg − (eu_prod + plus_prod + carbon_black + metal_scrap + losses)| ≤ 1%` — warning, non error
3. `0 ≤ theor_veg_pct ≤ 100` e `0 ≤ manuf_veg_pct ≤ 100`
4. Entry date non può essere futura
5. Soft delete: `deleted_at IS NULL` filtra i record "attivi" — mai hard delete da API
6. Audit log è append-only — non va mai modificato
7. Tutti i write su `daily_entries` generano riga `audit_log` con `old_values` e `new_values` (JSONB)
8. Supplier/contract referenziati in daily_entry devono essere `active = TRUE`

---

## 9. Stato sprint — cosa è fatto e cosa manca

### Sprint 1 — Foundation ✅ QUASI COMPLETO

| Issue | Titolo | Stato |
|-------|--------|-------|
| S1-1 | Docker Compose scaffold | ✅ DONE |
| S1-2 | .env.sample + secrets template | ✅ DONE |
| S1-3 | Alembic init + migrations suppliers/contracts/certificates | ✅ DONE |
| S1-4 | Migration daily_entries | ✅ DONE |
| S1-5 | Migration users + audit_log | ✅ DONE |
| S1-6 | Materialized views mass_balance_daily + monthly | ✅ DONE |
| S1-7 | FastAPI scaffold + /health | ✅ DONE (già in S1-1) |
| S1-8 | SQLAlchemy 2.0 models + Pydantic v2 schemas | ✅ DONE |
| S1-9 | Auth: bcrypt cost 12 + JWT + 4 ruoli + seed | ✅ DONE |
| S1-10 | CRUD suppliers/contracts/certificates + router wiring | ✅ DONE |
| S1-11 | CRUD daily_entries (soft delete + audit hook) | ✅ DONE |
| S1-12 | pytest fixtures + smoke tests | ✅ DONE (2 test files) |
| S1-13 | ruff + mypy strict + pre-commit | ✅ DONE |
| S1-14 | CI GitHub Actions (lint + test on PR) | ⏳ TODO |

### Sprint 2 — Ingest storico + reports ⏳ DA FARE

- Parser xlsx Girardot (pandas + openpyxl) → `scripts/ingest_xlsx.py`
- Script one-shot dry-run + report errori
- Endpoint `/reports/mass-balance`, `/reports/by-supplier`, `/reports/monthly`
- Endpoint `/daily-entries/bulk` (paste-from-excel)

### Sprint 3 — Frontend dashboard ⏳ DA FARE

- App Next.js 14 in `/frontend/` (attualmente solo Dockerfile stub)
- Layout + auth integration (NextAuth credentials)
- Dashboard KPI + grafici Recharts
- Tabella entries con filtri (TanStack Table)

### Sprint 4–6 — Data entry, PDF, deploy ⏳ DA FARE

- Form nuova entry (DailyEntryForm, 20+ campi)
- PDF via WeasyPrint (template ISCC/EU RED II)
- Deploy Docker su Hetzner
- QA E2E Playwright
- Training cliente

---

## 10. Pattern e convenzioni del codebase

### Backend Python

```python
# Dipendenza DB standard — usare sempre questo pattern
DbDep = Annotated[AsyncSession, Depends(get_db)]

# Utente corrente — da routers/auth.py
CurrentUser = Annotated[User, Depends(_get_current_user)]

# Query async — sempre await
result = await db.execute(select(Model).where(...))
obj = result.scalar_one_or_none()

# Pydantic v2 — usare model_dump(), NON .dict()
data = body.model_dump(exclude_unset=True)

# Soft delete — mai hard delete
obj.deleted_at = datetime.utcnow()

# Mass balance refresh — AUTOCOMMIT obbligatorio (non in transaction)
async with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
    await conn.execute(text("SELECT refresh_mass_balance_views()"))
```

### Migrations Alembic

- Prefisso numerico: `000N_descrizione.py`
- Prossima: `0009_...` o continuare sequenza
- Run: `alembic upgrade head` dentro container backend

### File import Excel

- **MAI** committare `*.xlsx` o dati cliente in git
- Il parser va in `scripts/ingest_xlsx.py`
- Dry-run mode obbligatorio prima di write reale

---

## 11. Decisioni aperte (da confermare con cliente)

| # | Domanda | Default blueprint |
|---|---------|------------------|
| 1 | Nome cliente definitivo | TBD |
| 2 | Multi-impianto futuro? | Solo Girardot |
| 3 | PDF template fornito da cliente | Template ISCC standard |
| 4 | Hosting Hetzner o cliente? | Hetzner XbitAgency |
| 5 | Auth SSO o gestita da noi | NextAuth credentials |
| 6 | Lingua UI | IT + EN |
| 7 | Storico 2024 da importare | No (solo 2025+) |
| 8 | Backup retention | 30gg daily + 12m monthly |
| 9 | Mobile UI obbligatoria? | Sì (tablet operatore impianto) |
| 10 | Integrazione ERP cliente | No (solo CSV/PDF export) |

---

## 12. Blocchi noti

| Blocco | Chi sblocca |
|--------|------------|
| S1-14 CI GitHub Actions | Developer — nessun blocco esterno |
| Sprint 2 parser xlsx | Accesso al file Drive: `1FWeZs6nxmM_STzFZLGFVpPCBU877Uukw` |
| Frontend app Next.js | Developer — inizia da Sprint 3 |
| Deploy Hetzner | DevOps — Docker compose già pronto |
| PDF template | Cliente deve approvare mock prima implementazione |
| Decisioni aperte §11 | Gianni + cliente |

---

## 13. Comandi frequenti

```bash
# Backend locale (dev)
cd backend && uvicorn app.main:app --reload --port 8000

# Alembic migrations
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "descrizione"

# Test
cd backend && pytest tests/

# Lint
cd backend && ruff check . && mypy .

# Docker Compose (tutto lo stack)
docker compose up -d
docker compose logs -f backend

# Ingest xlsx (quando implementato)
python scripts/ingest_xlsx.py --file path/to/file.xlsx --dry-run
```

---

## 14. Riferimenti

- **Blueprint completo:** `/mnt/c/Users/User/dft-project/BLUEPRINT.md`
- **File xlsx sorgente:** Drive `1FWeZs6nxmM_STzFZLGFVpPCBU877Uukw`
- **Folder Drive 2025:** `1jC39kiulY-6utuYsuhY2SgNqRpkQtiB5`
- **Plane progetto:** DFTEN (DFT Energy) — workspace xbitagency
- **Repo locale:** `/mnt/c/Users/User/dft-project/` — branch `main`
