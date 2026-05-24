from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ShipmentUnit(Base):
    __tablename__ = "shipment_unit"
    __table_args__ = (
        CheckConstraint(
            "kg_net > 0",
            name="shipment_unit_kg_net_positive",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    leg_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shipment_leg.id", ondelete="CASCADE"), nullable=False
    )
    container_ref: Mapped[str] = mapped_column(Text, nullable=False)
    flexitank_ref: Mapped[str | None] = mapped_column(Text)
    kg_gross: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    kg_tare: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    kg_net: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
