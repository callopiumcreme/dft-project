from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

AuditAction = Literal["INSERT", "UPDATE", "DELETE"]


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    action: AuditAction
    table_name: str
    record_id: int
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: datetime
