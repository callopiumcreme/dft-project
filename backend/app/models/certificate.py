from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'expired', 'suspended')",
            name="ck_certificates_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cert_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    scheme: Mapped[str] = mapped_column(String(20), server_default=text("'ISCC'"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'active'"), nullable=False)
    document_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
