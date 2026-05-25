from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.sql import text as sa_text

from app.db.base import Base


class ConsignmentPos(Base):
    """Proof-of-Sustainability row attached to a consignment.

    Cliente direction (2026-05-23): each PoS carries its own outbound eRSV
    number (CO/{yy}/{seq:03d}) and its own GHG value triple. A consignment
    with 20 PoS therefore generates 20 distinct outbound documents.

    Schema (migration 0028): surrogate ``id BIGSERIAL PRIMARY KEY`` —
    the natural key ``(consignment_id, pos_number)`` is enforced only on
    active rows by partial UNIQUE index ``ux_consignment_pos_active``.
    Soft-deleted rows (``deleted_at IS NOT NULL``) free their natural key
    so the same ``pos_number`` can be re-inserted after tombstoning.
    """

    __tablename__ = "consignment_pos"

    # Surrogate PK (0028) — single source of identity for the row.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    consignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("consignment.id", ondelete="CASCADE"),
        nullable=False,
    )
    pos_number: Mapped[str] = mapped_column(Text, nullable=False)
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

    # PoS document issuance date (added by migration 0027). Distinct from
    # consignment.delivered_uk (physical arrival) and from created_at (DB
    # insert). Drives warehouse 'pos_issue' debit timing.
    issuance_date: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column()

    # Partial UNIQUE on natural key for active rows only. Mirrors
    # ``ux_consignment_pos_active`` created in migration 0028. We model it
    # in the ORM so Alembic autogenerate stays in sync; the predicate uses
    # the PostgreSQL-specific ``postgresql_where`` kwarg.
    __table_args__ = (
        Index(
            "ux_consignment_pos_active",
            "consignment_id",
            "pos_number",
            unique=True,
            postgresql_where=sa_text("deleted_at IS NULL"),
        ),
    )
