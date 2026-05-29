# DFT Project — AgentOS Config

**Repo:** `/mnt/c/Users/User/dft-project/` | **Branch:** `main`
**Plane:** workspace `xbitagency`, project `DFTEN` (DFT Energy), project_id `b515ded8-3a55-4764-be0c-a010941e847f`

> Analisi approfondita completa: `docs/agentos-context.md` — LEGGI PRIMA DI AGIRE.

---

## Stack

- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0 async + Pydantic v2 + Alembic
- **DB:** PostgreSQL 16 — 43 migrations in `backend/alembic/versions/` (0001-0043)
- **Auth:** JWT Bearer, 8h TTL, ruoli: `admin|operator|viewer|certifier`
- **Frontend:** Next.js 14 App Router — `landing/` (deploy https://oistebio.usenexos.com via PM2 + nginx Hetzner). Sprint 3 estesa con `/app/*` protetto JWT (Sprint 3 chiuso 2026-05-21)
- **Proxy:** Caddy 2 (non nginx) — auto HTTPS
- **Containers:** Docker Compose (`db + backend + frontend + caddy`). NOTE: il servizio `frontend` nel compose è legacy (`frontend/` contiene solo un Dockerfile stale), l'app reale gira via `landing/` (PM2 host) o build container separato — vedi docs/sprint-3-frontend.md
- **Lint:** ruff + mypy strict + pre-commit (già configurati)

## Regole operative

1. **MAI committare** `*.xlsx`, `.env`, o dati cliente
2. **MAI hard delete** — usare soft delete (`deleted_at = NOW()`)
3. **MAI scrivere** `total_input_kg` — è colonna `GENERATED ALWAYS` (somma `car_kg + truck_kg + special_kg`)
4. **MAI eseguire** `REFRESH MATERIALIZED VIEW CONCURRENTLY` dentro transazione — usare AUTOCOMMIT (vedi `services/mv_refresh.py`)
5. **Pydantic v2:** `model_dump()` non `.dict()`
6. **Pre-implementation:** leggere BLUEPRINT.md prima di qualsiasi nuovo feature
7. **Migrations:** prefisso `00NN_descrizione.py`, prossima è `0044_`. Mai migration data che chiave UPDATE su id auto-increment (lezione 0016 — usare business keys)
8. **`audit_log.action` CHECK** ammette solo `{insert, update, delete, soft_delete, restore, pdf_sign}` — schema_extend NON ammesso (usare `action='update'` + tag in `new_values.kind`)
9. **NO writes prod senza parola esplicita** — "ok"/"go" = LOCAL only

## Stato sprint

| Sprint | Stato |
|--------|-------|
| Sprint 1 — Foundation | ✅ COMPLETO |
| Sprint 2 — Ingest xlsx + reports | ✅ COMPLETO (DFTEN-64..71 Done) |
| Sprint 3 — Frontend dashboard integrato | ✅ COMPLETO (chiuso 2026-05-21) |
| Audit-prep DfT C1 (Deeba) | 🚧 IN CORSO — audit submission 2026-05-27, deadline evidence 22 May 2026 PASSED |
| Sprint γ — utilities (DFTEN-103, 108, 164) | 🚧 IN CORSO 2026-05-29 (audit-safe) |
| Sprint α — feedstocks model (DFTEN E3 cluster) | ⏳ DEFERRED post-audit |
| Sprint β — Annex D GHG runtime | ⏳ DEFERRED post-α |

**Decisione Sprint 3:** single Next.js app — estendere `landing/` con `/app/*` protetto. NO `frontend/` separato.

## File critici

| File | Ruolo |
|------|-------|
| `BLUEPRINT.md` | Specifica completa — fonte di verità (in revisione v0.2 — daily_input / daily_production split) |
| `backend/app/main.py` | Entry point FastAPI |
| `backend/app/routers/daily_inputs.py` | Daily inputs (car_kg + truck_kg + special_kg → total_input_kg) + audit log |
| `backend/app/routers/daily_production.py` | Daily production output ledger |
| `backend/app/routers/mass_balance.py` | (NON ESISTE come file separato — endpoint mv refresh in `routers/admin.py` `POST /admin/refresh-mvs`; logica in `services/mv_refresh.py`) |
| `backend/app/routers/admin.py` | Admin CRUD users, audit-log read + CSV export, MV refresh |
| `backend/app/core/security.py` | JWT + bcrypt — legge `JWT_SECRET` env var |
| `backend/app/db/session.py` | engine + get_db() |
| `backend/alembic/versions/` | 43 migration files (0001-0043) |
| `docker-compose.yml` | Stack completo (db / backend / frontend / caddy + bind-mounts data/) |
| `docs/agentos-context.md` | Analisi approfondita AgentOS (rebaseline in corso DFTEN-164) |
| `docs/sprint-3-frontend.md` | Sprint 3 — piano frontend integrato in landing/ (archivio) |
| `docs/audit-dft-c1-deeba-realign/` | Audit-prep doc set DfT C1 |
| `landing/` | Next.js 14 app (marketing + `/app/*` dashboard) |

## Comandi

```bash
# Backend dev
cd backend && uvicorn app.main:app --reload --port 8000

# Migrations
cd backend && alembic upgrade head

# Test
cd backend && pytest tests/

# Lint
cd backend && ruff check . && mypy .

# Stack completo
docker compose up -d
```
