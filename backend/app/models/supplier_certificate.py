from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class SupplierCertificate(Base):
    __tablename__ = "supplier_certificates"

    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suppliers.id", ondelete="CASCADE"), primary_key=True
    )
    certificate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("certificates.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
