# DFT Project

Full-stack mass balance tracking system for biofuel/recycling plant operations.

## Status

🟡 **Pre-implementation** — Blueprint phase. See [BLUEPRINT.md](BLUEPRINT.md) for full architecture.

## Stack

- **Frontend:** Next.js 14 + Tailwind + shadcn/ui
- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0
- **Database:** PostgreSQL 16
- **PDF generation:** WeasyPrint
- **Deploy:** Docker Compose

## Features (planned)

- Daily entry logbook for incoming raw materials
- Mass balance closure verification (input vs output)
- Supplier / contract / certificate management
- Compliance reports (ISCC / EU RED II)
- PDF export for certifier
- Audit log (immutable)
- Multi-role auth (admin / operator / viewer / certifier)

## Quick start

> **Note:** scaffolding not yet implemented. Will be added in Sprint 1.

```bash
# clone repo
git clone https://github.com/callopiumcreme/dft-project.git
cd dft-project

# bring up stack
cp .env.sample .env
docker compose up -d

# frontend → http://localhost:3000
# backend → http://localhost:8000
# api docs → http://localhost:8000/docs
```

## Repository structure

```
dft-project/
├── BLUEPRINT.md       # full architecture & roadmap
├── README.md          # this file
├── docs/              # technical documentation
├── backend/           # FastAPI service
├── frontend/          # Next.js app
├── db/                # schema, seed, migrations
└── scripts/           # utility scripts (ingest, backup)
```

## Roadmap

| Sprint | Goal | ETA |
|--------|------|-----|
| 1 | Foundation: Docker + DB + auth + CRUD API | 1 week |
| 2 | Historical xlsx ingest + reports API | 3-4 days |
| 3 | Frontend dashboard + read-only views | 1 week |
| 4 | Data entry + admin panels | 1 week |
| 5 | PDF generation + production deploy | 3-4 days |
| 6 | QA + documentation + handover | 3-4 days |

## License

Proprietary — All rights reserved.

## Contributing

Internal project. Contact repo owner.
