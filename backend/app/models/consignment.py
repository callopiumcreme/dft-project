from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.off_taker import OffTaker


class Consignment(Base):
    __tablename__ = "consignment"
    __table_args__ = (
        CheckConstraint(
            "product_grade IN ('DEV-P100','DEV-P200')",
            name="consignment_product_grade_check",
        ),
        CheckConstraint(
            "status IN ('draft','loaded','in_transit','at_utb','delivered_uk','closed')",
            name="consignment_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    off_taker_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("off_taker.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    contract_ref: Mapped[str | None] = mapped_column(Text)
    product_grade: Mapped[str] = mapped_column(Text, nullable=False)
    prod_date_from: Mapped[date | None] = mapped_column(Date)
    prod_date_to: Mapped[date | None] = mapped_column(Date)
    total_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    ersv_outbound_no: Mapped[str | None] = mapped_column(Text)
    port_rsv_no: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="draft")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column()

    off_taker: Mapped[OffTaker] = relationship("OffTaker", lazy="raise")
