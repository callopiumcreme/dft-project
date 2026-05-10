from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','expired','revoked','placeholder')",
            name="certificates_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cert_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    scheme: Mapped[str] = mapped_column(Text, nullable=False, server_default="ISCC EU")
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="active")
    issued_at: Mapped[date | None] = mapped_column(Date)
    expires_at: Mapped[date | None] = mapped_column(Date)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    document_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column()

    suppliers: Mapped[list["Supplier"]] = relationship(  # noqa: F821
        secondary="supplier_certificates", back_populates="certificates", lazy="selectin"
    )

    @property
    def supplier_ids(self) -> list[int]:
        return [s.id for s in self.suppliers]
