from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConsignmentPos(Base):
    """Proof-of-Sustainability row attached to a consignment.

    Cliente direction (2026-05-23): each PoS carries its own outbound eRSV
    number (CO/{yy}/{seq:03d}) and its own GHG value triple. A consignment
    with 20 PoS therefore generates 20 distinct outbound documents.
    """

    __tablename__ = "consignment_pos"

    consignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("consignment.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pos_number: Mapped[str] = mapped_column(Text, primary_key=True, nullable=False)
    pdf_ref: Mapped[str | None] = mapped_column(Text)
    kg_net: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))

    # Per-PoS outbound eRSV number. Partial UNIQUE on (NOT NULL, deleted_at IS NULL).
    ersv_outbound_no: Mapped[str | None] = mapped_column(Text)

    # Per-PoS GHG values (ISCC PoS page 2). Units: gCO2eq/MJ for Ep/Etd/total;
    # percent for saving vs fossil baseline.
    ghg_ep: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ghg_etd: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ghg_total: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ghg_saving_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column()
