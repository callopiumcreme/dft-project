from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import Boolean, CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

UserRole = Literal["admin", "operator", "viewer", "certifier"]


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'operator', 'viewer', 'certifier')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("TRUE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
