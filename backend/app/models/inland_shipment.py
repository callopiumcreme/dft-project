"""Inland CO shipment row — one per ISO container Girardot plant → Cartagena port.

Mirrors the table created by alembic ``0023_inland_shipment``. Each row records
the per-container truth that drives a single eRSV inland document (Ley
527/1999, ES). The legacy ``shipment_leg`` table aggregates these rows into a
single ``bl_ocean`` leg keyed on the onward BL.

Soft-delete only (``deleted_at IS NOT NULL``); the UNIQUE indexes are partial
on ``deleted_at IS NULL`` so historical rows never block re-insertion.
"""
from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 — used in Mapped[...] at class scope
from decimal import Decimal  # noqa: TC003 — used in Mapped[...] at class scope

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class InlandShipment(Base):
    __tablename__ = "inland_shipment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    consignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("consignment.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bl_ref: Mapped[str] = mapped_column(Text, nullable=False)
    seq_in_bl: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    container_id: Mapped[str] = mapped_column(String(11), nullable=False)
    seal_ref: Mapped[str | None] = mapped_column(Text)
    load_date: Mapped[date] = mapped_column(Date, nullable=False)
    gross_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    tare_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    net_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    ersv_inland_no: Mapped[str | None] = mapped_column(Text)
    transporter: Mapped[str | None] = mapped_column(Text)
    driver_name: Mapped[str | None] = mapped_column(Text)
    vehicle_plate: Mapped[str | None] = mapped_column(Text)
    origin_node: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="Girardot plant (CO)",
    )
    destination_node: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="Cartagena Contecar (CO)",
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column()
