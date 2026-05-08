"""seed data: suppliers, contracts, certificates

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-07

"""
from __future__ import annotations

from datetime import date

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str = "0006"
branch_labels: str | None = None
depends_on: str | None = None

suppliers_table = sa.table(
    "suppliers",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("code", sa.String),
    sa.column("country", sa.String),
    sa.column("active", sa.Boolean),
    sa.column("notes", sa.Text),
)

contracts_table = sa.table(
    "contracts",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("supplier_id", sa.Integer),
    sa.column("start_date", sa.Date),
    sa.column("end_date", sa.Date),
    sa.column("total_kg_committed", sa.Numeric),
    sa.column("notes", sa.Text),
)

certificates_table = sa.table(
    "certificates",
    sa.column("id", sa.Integer),
    sa.column("cert_number", sa.String),
    sa.column("supplier_id", sa.Integer),
    sa.column("issued_at", sa.Date),
    sa.column("expires_at", sa.Date),
    sa.column("scheme", sa.String),
    sa.column("status", sa.String),
    sa.column("document_url", sa.Text),
)

SUPPLIERS = [
    {
        "id": 1,
        "name": "EcoTire Colombia S.A.S.",
        "code": "ECO-CO-001",
        "country": "CO",
        "active": True,
        "notes": "Primary UCO/tire supplier — Barranquilla plant",
    },
    {
        "id": 2,
        "name": "GreenFuel Recycling Ltd.",
        "code": "GFR-GB-002",
        "country": "GB",
        "active": True,
        "notes": "UK-based pyrolysis oil trader",
    },
    {
        "id": 3,
        "name": "BioPetrol Cartagena",
        "code": "BPC-CO-003",
        "country": "CO",
        "active": True,
        "notes": "UCO collector — Caribbean coast",
    },
    {
        "id": 4,
        "name": "Renovar Energy S.p.A.",
        "code": "REN-IT-004",
        "country": "IT",
        "active": True,
        "notes": "Italian biomass feedstock aggregator",
    },
    {
        "id": 5,
        "name": "SustainOil Panamá",
        "code": "SOP-PA-005",
        "country": "PA",
        "active": False,
        "notes": "Suspended — certificate expired 2025-12",
    },
]

CONTRACTS = [
    {
        "id": 1,
        "code": "CTR-2026-001",
        "supplier_id": 1,
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "total_kg_committed": 500000.00,
        "notes": "Annual tire pyrolysis feedstock",
    },
    {
        "id": 2,
        "code": "CTR-2026-002",
        "supplier_id": 2,
        "start_date": date(2026, 3, 1),
        "end_date": date(2026, 8, 31),
        "total_kg_committed": 200000.00,
        "notes": "Pyrolysis oil spot contract H1",
    },
    {
        "id": 3,
        "code": "CTR-2026-003",
        "supplier_id": 3,
        "start_date": date(2026, 1, 15),
        "end_date": date(2026, 12, 31),
        "total_kg_committed": 350000.00,
        "notes": "UCO collection agreement",
    },
    {
        "id": 4,
        "code": "CTR-2026-004",
        "supplier_id": 4,
        "start_date": date(2026, 4, 1),
        "end_date": None,
        "total_kg_committed": None,
        "notes": "Open-ended biomass supply framework",
    },
    {
        "id": 5,
        "code": "CTR-2025-010",
        "supplier_id": 5,
        "start_date": date(2025, 6, 1),
        "end_date": date(2025, 12, 31),
        "total_kg_committed": 100000.00,
        "notes": "Expired — supplier suspended",
    },
]

CERTIFICATES = [
    {
        "id": 1,
        "cert_number": "ISCC-EU-2026-00451",
        "supplier_id": 1,
        "issued_at": date(2026, 1, 10),
        "expires_at": date(2027, 1, 9),
        "scheme": "ISCC",
        "status": "active",
        "document_url": None,
    },
    {
        "id": 2,
        "cert_number": "ISCC-PLUS-2026-00822",
        "supplier_id": 1,
        "issued_at": date(2026, 2, 15),
        "expires_at": date(2027, 2, 14),
        "scheme": "ISCC",
        "status": "active",
        "document_url": None,
    },
    {
        "id": 3,
        "cert_number": "ISCC-EU-2026-01133",
        "supplier_id": 2,
        "issued_at": date(2026, 3, 1),
        "expires_at": date(2027, 2, 28),
        "scheme": "ISCC",
        "status": "active",
        "document_url": None,
    },
    {
        "id": 4,
        "cert_number": "ISCC-EU-2025-09344",
        "supplier_id": 3,
        "issued_at": date(2025, 9, 20),
        "expires_at": date(2026, 9, 19),
        "scheme": "ISCC",
        "status": "active",
        "document_url": None,
    },
    {
        "id": 5,
        "cert_number": "REDII-IT-2026-00067",
        "supplier_id": 4,
        "issued_at": date(2026, 4, 5),
        "expires_at": date(2027, 4, 4),
        "scheme": "REDII",
        "status": "active",
        "document_url": None,
    },
    {
        "id": 6,
        "cert_number": "ISCC-EU-2025-04455",
        "supplier_id": 5,
        "issued_at": date(2025, 6, 1),
        "expires_at": date(2025, 12, 1),
        "scheme": "ISCC",
        "status": "expired",
        "document_url": None,
    },
    {
        "id": 7,
        "cert_number": "ISCC-PLUS-2026-01500",
        "supplier_id": 3,
        "issued_at": date(2026, 1, 20),
        "expires_at": date(2027, 1, 19),
        "scheme": "ISCC",
        "status": "active",
        "document_url": None,
    },
    {
        "id": 8,
        "cert_number": "REDII-IT-2026-00102",
        "supplier_id": 4,
        "issued_at": date(2026, 5, 1),
        "expires_at": None,
        "scheme": "REDII",
        "status": "suspended",
        "document_url": None,
    },
]


def upgrade() -> None:
    op.bulk_insert(suppliers_table, SUPPLIERS)
    op.bulk_insert(contracts_table, CONTRACTS)
    op.bulk_insert(certificates_table, CERTIFICATES)

    # Reset sequences to avoid PK collision on next INSERT
    op.execute("SELECT setval('suppliers_id_seq', (SELECT MAX(id) FROM suppliers))")
    op.execute("SELECT setval('contracts_id_seq', (SELECT MAX(id) FROM contracts))")
    op.execute("SELECT setval('certificates_id_seq', (SELECT MAX(id) FROM certificates))")


def downgrade() -> None:
    op.execute("DELETE FROM certificates WHERE id <= 8")
    op.execute("DELETE FROM contracts WHERE id <= 5")
    op.execute("DELETE FROM suppliers WHERE id <= 5")
