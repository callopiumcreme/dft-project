from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    country: Mapped[str] = mapped_column(String(2), server_default=text("'CO'"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("TRUE"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
