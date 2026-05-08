from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class DailyInput(Base):
    __tablename__ = "daily_inputs"
    __table_args__ = (
        CheckConstraint(
            "car_kg >= 0 AND truck_kg >= 0 AND special_kg >= 0",
            name="daily_inputs_kg_nonneg",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    entry_time: Mapped[time | None] = mapped_column(Time)
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    certificate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("certificates.id", ondelete="RESTRICT")
    )
    contract_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("contracts.id", ondelete="RESTRICT")
    )
    ersv_number: Mapped[str | None] = mapped_column(Text)
    car_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, server_default="0")
    truck_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, server_default="0")
    special_kg: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, server_default="0")
    total_input_kg: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        Computed("car_kg + truck_kg + special_kg", persisted=True),
    )
    theor_veg_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    manuf_veg_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    c14_analysis: Mapped[str | None] = mapped_column(Text)
    c14_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    source_file: Mapped[str | None] = mapped_column(Text)
    source_row: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
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
