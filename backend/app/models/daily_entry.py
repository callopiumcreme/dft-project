from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"), nullable=True)
    certificate_id: Mapped[int | None] = mapped_column(ForeignKey("certificates.id"), nullable=True)
    ersv_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    car_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), server_default=text("0"), nullable=True)
    truck_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), server_default=text("0"), nullable=True)
    special_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), server_default=text("0"), nullable=True)
    # total_input_kg is GENERATED ALWAYS AS, read-only
    total_input_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    theor_veg_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    manuf_veg_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    kg_to_production: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    eu_prod_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    plus_prod_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    c14_analysis: Mapped[bool | None] = mapped_column(Boolean, server_default=text("FALSE"), nullable=True)
    c14_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    carbon_black_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    metal_scrap_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    h2o_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    gas_syngas_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    losses_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    output_eu_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    contract_ref: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pos_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_row: Mapped[int | None] = mapped_column(nullable=True)
    created_by: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
