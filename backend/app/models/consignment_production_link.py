from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConsignmentProductionLink(Base):
    __tablename__ = "consignment_production_link"
    __table_args__ = (
        CheckConstraint(
            "kg_allocated > 0",
            name="consignment_production_link_kg_allocated_positive",
        ),
    )

    consignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("consignment.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prod_date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)
    kg_allocated: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
