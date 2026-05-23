from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConsignmentPos(Base):
    __tablename__ = "consignment_pos"

    consignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("consignment.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pos_number: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    pdf_ref: Mapped[str | None] = mapped_column(Text)
    kg_net: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
