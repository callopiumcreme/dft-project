from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class C14Certificate(Base):
    """FMS Appendix A — C14 Laboratory Certificate (radiocarbon analysis).

    One row per monthly bio-based carbon content certificate (EN 16640
    Annex B) for DEV-P100. PDF resolved by cert_number under
    data/c14/<cert_number>.pdf (bind-mount, no Drive at runtime).
    """

    __tablename__ = "c14_certificates"

    id: Mapped[int] = mapped_column(primary_key=True)
    cert_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    lab: Mapped[str | None] = mapped_column(Text)
    product: Mapped[str | None] = mapped_column(Text)
    period_month: Mapped[date | None] = mapped_column(Date)
    sampled_date: Mapped[date | None] = mapped_column(Date)
    tested_date: Mapped[date | None] = mapped_column(Date)
    report_date: Mapped[date | None] = mapped_column(Date)
    bio_carbon_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    method: Mapped[str | None] = mapped_column(Text)
    sample_ref: Mapped[str | None] = mapped_column(Text)
    batch_ref: Mapped[str | None] = mapped_column(Text)
    sustainability_decl: Mapped[str | None] = mapped_column(Text)
    pdf_filename: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column()
