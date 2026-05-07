# DFT Project — AgentOS Config

**Repo:** `/mnt/c/Users/User/dft-project/` | **Branch:** `main`
**Plane:** workspace `xbitagency`, project `DFTEN` (DFT Energy), project_id `b515ded8-3a55-4764-be0c-a010941e847f`

> Analisi approfondita completa: `docs/agentos-context.md` — LEGGI PRIMA DI AGIRE.

---

## Stack

- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0 async + Pydantic v2 + Alembic
- **DB:** PostgreSQL 16 — 8 migrations in `backend/alembic/versions/`
- **Auth:** JWT Bearer, 8h TTL, ruoli: `admin|operator|viewer|certifier`
- **Frontend:** Next.js 14 App Router (stub — non ancora implementato)
- **Proxy:** Caddy 2 (non nginx) — auto HTTPS
- **Containers:** Docker Compose (`db + backend + frontend + caddy`)
- **Lint:** ruff + mypy strict + pre-commit (già configurati)

## Regole operative

1. **MAI committare** `*.xlsx`, `.env`, o dati cliente
2. **MAI hard delete** — usare soft delete (`deleted_at = NOW()`)
3. **MAI scrivere** `total_input_kg` — è colonna `GENERATED ALWAYS`
4. **MAI eseguire** `REFRESH MATERIALIZED VIEW CONCURRENTLY` dentro transazione — usare AUTOCOMMIT (vedi `routers/mass_balance.py`)
5. **Pydantic v2:** `model_dump()` non `.dict()`
6. **Pre-implementation:** leggere BLUEPRINT.md prima di qualsiasi nuovo feature
7. **Migrations:** prefisso `000N_descrizione.py`, prossima è `0009_`

## Stato sprint

| Sprint | Stato |
|--------|-------|
| Sprint 1 — Foundation | ✅ QUASI COMPLETO (manca S1-14 CI) |
| Sprint 2 — Ingest xlsx + reports | ⏳ TODO |
| Sprint 3 — Frontend dashboard | ⏳ TODO (frontend è stub) |
| Sprint 4-6 — Data entry, PDF, deploy | ⏳ TODO |

## File critici

| File | Ruolo |
|------|-------|
| `BLUEPRINT.md` | Specifica completa — fonte di verità |
| `backend/app/main.py` | Entry point FastAPI |
| `backend/app/routers/daily_entries.py` | Router principale + audit log |
| `backend/app/routers/mass_balance.py` | Endpoint mv refresh (AUTOCOMMIT) |
| `backend/app/core/security.py` | JWT + bcrypt |
| `backend/app/db/session.py` | engine + get_db() |
| `backend/alembic/versions/` | 8 migration files (0001-0008) |
| `docker-compose.yml` | Stack completo |
| `docs/agentos-context.md` | Analisi approfondita AgentOS |

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
