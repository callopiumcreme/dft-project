from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ProductPurchase(Base):
    """Supplier-issued Sustainability Declaration (PoS) for purchased feedstock.

    One row per upstream PoS (e.g. ES2025-014, KAL-OIS-007). PDF resolved by
    pos_number under data/pos/<pos_number>.pdf (bind-mount, no Drive runtime).
    """

    __tablename__ = "product_purchases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pos_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="SET NULL")
    )
    certificate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("certificates.id", ondelete="SET NULL")
    )
    contract_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("contracts.id", ondelete="SET NULL")
    )
    issuance_date: Mapped[date | None] = mapped_column(Date)
    dispatch_label: Mapped[str | None] = mapped_column(Text)
    quantity_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    feedstock: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column()
