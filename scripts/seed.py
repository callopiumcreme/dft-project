"""Standalone seed script — suppliers, contracts, certificates.

Usage:
    DATABASE_URL=postgresql+asyncpg://dft:dft@localhost:5432/dft python scripts/seed.py

Idempotent: uses INSERT ... ON CONFLICT DO NOTHING.
"""
from __future__ import annotations

import asyncio
import os
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://dft:dft@db:5432/dft",
)

SUPPLIERS = [
    (1, "EcoTire Colombia S.A.S.", "ECO-CO-001", "CO", True, "Primary UCO/tire supplier — Barranquilla plant"),
    (2, "GreenFuel Recycling Ltd.", "GFR-GB-002", "GB", True, "UK-based pyrolysis oil trader"),
    (3, "BioPetrol Cartagena", "BPC-CO-003", "CO", True, "UCO collector — Caribbean coast"),
    (4, "Renovar Energy S.p.A.", "REN-IT-004", "IT", True, "Italian biomass feedstock aggregator"),
    (5, "SustainOil Panamá", "SOP-PA-005", "PA", False, "Suspended — certificate expired 2025-12"),
]

CONTRACTS = [
    (1, "CTR-2026-001", 1, date(2026, 1, 1), date(2026, 12, 31), 500000.00, "Annual tire pyrolysis feedstock"),
    (2, "CTR-2026-002", 2, date(2026, 3, 1), date(2026, 8, 31), 200000.00, "Pyrolysis oil spot contract H1"),
    (3, "CTR-2026-003", 3, date(2026, 1, 15), date(2026, 12, 31), 350000.00, "UCO collection agreement"),
    (4, "CTR-2026-004", 4, date(2026, 4, 1), None, None, "Open-ended biomass supply framework"),
    (5, "CTR-2025-010", 5, date(2025, 6, 1), date(2025, 12, 31), 100000.00, "Expired — supplier suspended"),
]

CERTIFICATES = [
    (1, "ISCC-EU-2026-00451", 1, date(2026, 1, 10), date(2027, 1, 9), "ISCC", "active"),
    (2, "ISCC-PLUS-2026-00822", 1, date(2026, 2, 15), date(2027, 2, 14), "ISCC", "active"),
    (3, "ISCC-EU-2026-01133", 2, date(2026, 3, 1), date(2027, 2, 28), "ISCC", "active"),
    (4, "ISCC-EU-2025-09344", 3, date(2025, 9, 20), date(2026, 9, 19), "ISCC", "active"),
    (5, "REDII-IT-2026-00067", 4, date(2026, 4, 5), date(2027, 4, 4), "REDII", "active"),
    (6, "ISCC-EU-2025-04455", 5, date(2025, 6, 1), date(2025, 12, 1), "ISCC", "expired"),
    (7, "ISCC-PLUS-2026-01500", 3, date(2026, 1, 20), date(2027, 1, 19), "ISCC", "active"),
    (8, "REDII-IT-2026-00102", 4, date(2026, 5, 1), None, "REDII", "suspended"),
]


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        for row in SUPPLIERS:
            await conn.execute(
                text(
                    "INSERT INTO suppliers (id, name, code, country, active, notes) "
                    "VALUES (:id, :name, :code, :country, :active, :notes) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": row[0], "name": row[1], "code": row[2], "country": row[3], "active": row[4], "notes": row[5]},
            )
        print(f"  suppliers: {len(SUPPLIERS)} rows")

        for row in CONTRACTS:
            await conn.execute(
                text(
                    "INSERT INTO contracts (id, code, supplier_id, start_date, end_date, total_kg_committed, notes) "
                    "VALUES (:id, :code, :supplier_id, :start_date, :end_date, :total_kg_committed, :notes) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": row[0], "code": row[1], "supplier_id": row[2],
                    "start_date": row[3], "end_date": row[4],
                    "total_kg_committed": row[5], "notes": row[6],
                },
            )
        print(f"  contracts: {len(CONTRACTS)} rows")

        for row in CERTIFICATES:
            await conn.execute(
                text(
                    "INSERT INTO certificates (id, cert_number, supplier_id, issued_at, expires_at, scheme, status) "
                    "VALUES (:id, :cert_number, :supplier_id, :issued_at, :expires_at, :scheme, :status) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": row[0], "cert_number": row[1], "supplier_id": row[2],
                    "issued_at": row[3], "expires_at": row[4],
                    "scheme": row[5], "status": row[6],
                },
            )
        print(f"  certificates: {len(CERTIFICATES)} rows")

        # Reset sequences after explicit ID inserts
        await conn.execute(text("SELECT setval('suppliers_id_seq', (SELECT MAX(id) FROM suppliers))"))
        await conn.execute(text("SELECT setval('contracts_id_seq', (SELECT MAX(id) FROM contracts))"))
        await conn.execute(text("SELECT setval('certificates_id_seq', (SELECT MAX(id) FROM certificates))"))

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
