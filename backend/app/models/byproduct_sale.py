"""ORM model: byproduct_sale.

Per-invoice row for non-EU byproduct sales (plus-oil / carbon black /
metal scrap). A successful sale also writes a companion row in
``mass_balance_ledger`` (event_type='byproduct_sale'); soft-delete writes
a reversal ledger row. See ``app/routers/byproduct_sales.py`` for the
transactional contract.

Schema: alembic/versions/0026_warehouse_inventory.py (table
``byproduct_sale``). CHECK constraints enforce
``product_kind IN ('plus_oil','carbon_black','metal_scrap')`` and
``kg_net > 0`` — mirrored here so SQLAlchemy schema reflection /
metadata operations stay consistent with the live DB.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.byproduct_buyer import ByproductBuyer


class ByproductSale(Base):
    __tablename__ = "byproduct_sale"
    __table_args__ = (
        CheckConstraint(
            "product_kind IN ('plus_oil','carbon_black','metal_scrap')",
            name="byproduct_sale_product_kind_check",
        ),
        CheckConstraint(
            "kg_net > 0",
            name="byproduct_sale_kg_net_positive",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_kind: Mapped[str] = mapped_column(Text, nullable=False)
    buyer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("byproduct_buyer.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    kg_net: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    invoice_no: Mapped[str | None] = mapped_column(Text)
    price_eur: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
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

    buyer: Mapped[ByproductBuyer] = relationship("ByproductBuyer", lazy="raise")
