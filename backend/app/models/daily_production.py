from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Computed, Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class DailyProduction(Base):
    __tablename__ = "daily_production"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    prod_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    kg_to_production: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    eu_prod_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    plus_prod_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    carbon_black_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    metal_scrap_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    h2o_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    gas_syngas_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    losses_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    output_eu_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    # GENERATED ALWAYS — read-only. Never write to litres_eu / litres_plus.
    litres_eu: Mapped[Decimal | None] = mapped_column(
        Numeric,
        Computed("eu_prod_kg / 0.78", persisted=True),
    )
    litres_plus: Mapped[Decimal | None] = mapped_column(
        Numeric,
        Computed("plus_prod_kg / 0.856", persisted=True),
    )
    contract_ref: Mapped[str | None] = mapped_column(Text)
    pos_number: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    source_file: Mapped[str | None] = mapped_column(Text)
    source_row: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column()
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
