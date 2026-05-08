"""Audit log helper — JSON-safe model snapshot + insert."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def _jsonify(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def model_snapshot(obj: Any) -> dict[str, Any]:
    """Map ORM instance to JSON-safe dict of column values."""
    mapper = inspect(obj).mapper
    return {col.key: _jsonify(getattr(obj, col.key)) for col in mapper.column_attrs}


async def write_audit(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: int,
    action: str,
    old_values: dict[str, Any] | None,
    new_values: dict[str, Any] | None,
    changed_by: int | None,
) -> None:
    db.add(
        AuditLog(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            changed_by=changed_by,
        )
    )
