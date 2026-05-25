"""Mass-balance ledger — append-only chain-of-custody event log.

Single source of truth for chain-of-custody per
``docs/mass-balance-allocation-policy.md`` v1.0. One row per flow event
(inbound feedstock, daily production, consignment assignment, inland
dispatch, ocean BL load, UTB transload, PoS issuance, UK delivery,
correction, opening, byproduct sale, syngas burn, h2o vent).

Append-only with soft-delete. Corrections are issued as NEW rows that
reference the superseded id via ``corrects_id`` — never UPDATE.

Live schema mirrors alembic ``0024_mass_balance_ledger`` plus the
``product_kind`` column and the extended event_type set added by
``0026_warehouse_inventory``. Documented (not migrated) here because
these tables already exist in DB and this ticket only adds ORM mapping.
"""
from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 — used in Mapped[...] at class scope
from decimal import Decimal  # noqa: TC003 — used in Mapped[...] at class scope

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base

# Allowed event_type values (live DB CHECK constraint).
EVENT_TYPES: tuple[str, ...] = (
    "inbound",
    "production",
    "consign_assign",
    "inland_dispatch",
    "bl_load",
    "utb_transload",
    "pos_issue",
    "uk_delivery",
    "correction",
    "opening",
    "byproduct_sale",
    "syngas_burn",
    "h2o_vent",
)

# Allowed product_kind values (live DB CHECK constraint, default 'eu_oil').
PRODUCT_KINDS: tuple[str, ...] = (
    "eu_oil",
    "plus_oil",
    "carbon_black",
    "metal_scrap",
    "syngas",
    "h2o",
)


class MassBalanceLedger(Base):
    __tablename__ = "mass_balance_ledger"
    __table_args__ = (
        CheckConstraint(
            "event_type IN (" + ", ".join(f"'{t}'" for t in EVENT_TYPES) + ")",
            name="mass_balance_ledger_event_type_check",
        ),
        CheckConstraint(
            "product_kind IN (" + ", ".join(f"'{k}'" for k in PRODUCT_KINDS) + ")",
            name="mass_balance_ledger_product_kind_check",
        ),
        CheckConstraint(
            "kg_in IS NOT NULL OR kg_out IS NOT NULL",
            name="mass_balance_ledger_kg_at_least_one",
        ),
        CheckConstraint(
            "(kg_in IS NULL OR kg_in >= 0) AND (kg_out IS NULL OR kg_out >= 0)",
            name="mass_balance_ledger_kg_nonneg",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    kg_in: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    kg_out: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    ref_table: Mapped[str] = mapped_column(Text, nullable=False)
    ref_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ref_doc_no: Mapped[str | None] = mapped_column(Text)
    consignment_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("consignment.id", ondelete="RESTRICT"),
    )
    prev_balance_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    post_balance_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    corrects_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("mass_balance_ledger.id", ondelete="RESTRICT"),
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column()
    product_kind: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="eu_oil",
    )
