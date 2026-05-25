"""ORM model: byproduct_buyer.

Lightweight counterparty table for non-EU byproduct streams (plus-oil,
carbon black, metal scrap). One row per buyer; soft-delete via
``deleted_at`` with a partial unique index on ``name`` (where
``deleted_at IS NULL``) so historical names can be re-used after a
soft-delete.

Schema: alembic/versions/0026_warehouse_inventory.py (table
``byproduct_buyer``).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ByproductBuyer(Base):
    __tablename__ = "byproduct_buyer"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str | None] = mapped_column(Text)
    vat: Mapped[str | None] = mapped_column(Text)
    contact: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
