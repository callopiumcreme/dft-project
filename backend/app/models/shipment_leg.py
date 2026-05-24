from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ShipmentLeg(Base):
    __tablename__ = "shipment_leg"
    __table_args__ = (
        CheckConstraint(
            "leg_type IN ('plant_to_port','port_loading','bl_ocean',"
            "'utb_transload','nl_to_uk_export','delivery_uk')",
            name="shipment_leg_leg_type_check",
        ),
        CheckConstraint(
            "document_type IN ('eRSV_outbound','Port_RSV','BL_ocean',"
            "'transload_report','MRN','BL_road','commercial_invoice')",
            name="shipment_leg_document_type_check",
        ),
        CheckConstraint(
            "kg_in >= kg_out",
            name="shipment_leg_no_mass_creation",
        ),
        CheckConstraint(
            "leg_type <> 'utb_transload' OR "
            "(kg_stock_residual IS NOT NULL AND kg_in = kg_out + kg_stock_residual)",
            name="shipment_leg_utb_mass_conservation",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    consignment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consignment.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    leg_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_ref: Mapped[str | None] = mapped_column(Text)
    document_date: Mapped[date | None] = mapped_column(Date)
    carrier: Mapped[str | None] = mapped_column(Text)
    origin_node: Mapped[str] = mapped_column(Text, nullable=False)
    destination_node: Mapped[str] = mapped_column(Text, nullable=False)
    kg_in: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    kg_out: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    kg_stock_residual: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    operator_certificate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("certificates.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column()
