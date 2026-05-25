"""EAD (Export Accompanying Document) row — 1:1 with ConsignmentPos.

Filed by BiNova BV as NL customs declarant for OisteBio Swiss GmbH (OisteBio
cannot file NL export customs directly). Each container shipment produces one
DMS Export Accompanying Document with a globally-unique MRN.

PDF is stored on disk under ``/data/customs/c-<consignment_id>/...`` and served
through an auth-gated streaming endpoint — **no Drive runtime dependency**.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConsignmentPosCustoms(Base):
    __tablename__ = "consignment_pos_customs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    consignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("consignment.id", ondelete="CASCADE"),
        nullable=False,
    )
    pos_number: Mapped[str] = mapped_column(Text, nullable=False)
    mrn: Mapped[str] = mapped_column(Text, nullable=False)
    lrn: Mapped[str | None] = mapped_column(Text)
    customs_office: Mapped[str | None] = mapped_column(Text)
    container_no: Mapped[str | None] = mapped_column(Text)
    gross_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    net_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    invoice_no: Mapped[str | None] = mapped_column(Text)
    declarant_name: Mapped[str | None] = mapped_column(Text)
    declarant_vat: Mapped[str | None] = mapped_column(Text)
    issuing_date: Mapped[date | None] = mapped_column(Date)
    pdf_ref: Mapped[str | None] = mapped_column(Text)
    # Path of the OisteBio→Crown Oil commercial invoice PDF, relative to
    # ``/data/invoices`` (added in alembic 0031). Streamed via auth-gated
    # endpoint, same pattern as ``pdf_ref`` for the EAD.
    invoice_pdf_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column()
