from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

UserRole = Literal["admin", "operator", "viewer", "certifier"]


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    active: bool | None = None
    password: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    last_login_at: datetime | None = None
